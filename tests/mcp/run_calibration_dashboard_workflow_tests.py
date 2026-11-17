#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Shared native steps, registered MCP interfaces, and real Lunar/PRISM execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != python.parent.parent.resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
# The local project environment supplies SymPy to the native unit suite; Lunar
# supplies PRISM/MCP. There are no model/provider/compiler calls in this workflow.
project_packages = sorted((ROOT / ".venv/lib").glob("python*/site-packages"))
for path in project_packages:
    sys.path.append(str(path))
os.environ["PYTHONPATH"] = os.pathsep.join(
    [*(str(p) for p in project_packages), os.environ.get("PYTHONPATH", "")]
)
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]

import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from calibration_mount import mount, configure
from calibration_dashboard_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_calibration_dashboard_workflow/workflow.yaml"
ORDER = [
    "initialize",
    "derivation",
    "grounding",
    "redefinition",
    "units",
    "summarize",
    "publish",
]


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def stable(payload):
    payload = deepcopy(payload)
    payload["execution"].pop("wall_seconds")
    for row in payload["execution"]["runs"]:
        row.pop("wall_seconds")
    return payload


def oracle():
    name = "calibration_original"
    spec = importlib.util.spec_from_loader(
        name,
        SourceFileLoader(
            name, str(ROOT / "tests/mcp/fixtures/calibration_original.py.txt")
        ),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cli(module, argv):
    old = sys.argv
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["calibration", *argv]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = module.main()
            except SystemExit as error:
                code = error.code
        return code, stdout.getvalue(), stderr.getvalue()
    finally:
        sys.argv = old


class CalibrationTests(unittest.TestCase):
    def test_native_equivalence_and_state(self):
        native, original = source(), oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mount(root)
            configure(native, root)
            configure(original, root)
            for json_mode in [False, True]:
                args = ["--output", str(root / "dashboard.json")] + (
                    ["--json"] if json_mode else []
                )
                expected = cli(original, args)
                expected_file = json.loads((root / "dashboard.json").read_text())
                actual = cli(native, args)
                actual_file = json.loads((root / "dashboard.json").read_text())
                self.assertEqual(actual[0], expected[0])
                self.assertEqual(actual[2], expected[2])
                self.assertEqual(stable(actual_file), stable(expected_file))
                (
                    self.assertEqual(
                        stable(json.loads(actual[1])), stable(json.loads(expected[1]))
                    )
                    if json_mode
                    else self.assertEqual(actual[1], "PASS\n")
                )
            initialized = native.initialize([])
            self.assertEqual(
                initialized,
                {
                    "options": {"output": str(native.DEFAULT_OUTPUT), "json": False},
                    "state": {"runs": [], "rows": {}},
                },
            )
            state = initialized["state"]
            for index, step in enumerate(
                [
                    native.derivation,
                    native.grounding,
                    native.redefinition,
                    native.units,
                ],
                1,
            ):
                prior = deepcopy(state)
                state = step(state)
                self.assertEqual(len(state["runs"]), index)
                self.assertEqual(len(state["rows"]), index)
                self.assertEqual(state["runs"][:-1], prior["runs"])
                self.assertTrue(
                    all(state["rows"][k] == v for k, v in prior["rows"].items())
                )
            self.assertEqual(
                [list(map(list, rows)) for rows in state["rows"].values()],
                [
                    [[True, True], [True, True], [False, False]],
                    [[True, True], [False, False], [False, False]],
                    [[True, True], [False, False]],
                    [[False, False], [True, True], [True, True]],
                ],
            )
            payload = native.summarize(state)
            self.assertEqual(payload["evaluation_sets"]["curated_regressions"], 11)
            self.assertEqual(payload["execution"]["subprocess_count"], 4)
            self.assertTrue(
                all(row["accuracy"] == 1 for row in payload["metrics"].values())
            )
            self.assertEqual(
                native.confusion([]),
                dict(
                    samples=0,
                    true_positive=0,
                    true_negative=0,
                    false_positive=0,
                    false_negative=0,
                    false_positive_rate=0.0,
                    false_negative_rate=0.0,
                    accuracy=0.0,
                ),
            )
            mixed = native.confusion(
                [(True, False), (False, True), (True, True), (False, False)]
            )
            self.assertEqual(
                [
                    mixed[k]
                    for k in [
                        "true_positive",
                        "true_negative",
                        "false_positive",
                        "false_negative",
                    ]
                ],
                [1, 1, 1, 1],
            )
            self.assertEqual(mixed["accuracy"], 0.5)
            for args in [["--unknown"], ["--output"]]:
                self.assertEqual(cli(native, args)[0], cli(original, args)[0])
            # Genuine process failures and invalid JSON, with no replaced source step.
            with self.assertRaisesRegex(RuntimeError, "diagnostic"):
                native.run_json(
                    [
                        sys.executable,
                        "-c",
                        'import sys; print("diagnostic",file=sys.stderr); sys.exit(7)',
                    ]
                )
            with self.assertRaises(json.JSONDecodeError):
                native.run_json([sys.executable, "-c", 'print("invalid JSON")'])

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_mathformerphysicslib_calibration_dashboard_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 7},
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mount(root)
            config = StdioConfig(
                command=sys.executable,
                args=[
                    str(ROOT / "tests/mcp/fixtures/calibration_server.py"),
                    str(root),
                ],
                cwd=str(ROOT),
            )
            failure = None
            async with manager.open(
                "calibration", config, {"PYTHONPATH": os.environ["PYTHONPATH"]}
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compile(doc):
                        assets = snapshot(doc)
                        result = compile_workflow(
                            "mcp:calibration",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )
                        self.assertTrue(result["runnable"], result["diagnostics"])
                        self.assertTrue(result["runtime_source"])
                        self.assertEqual(set(result["bindings"]), set(ORDER))
                        return result, assets

                    compiled, assets = compile(document)

                    async def authorize():
                        pass

                    async def run(argv, doc=None):
                        c, a = compile(doc) if doc else (compiled, assets)
                        print(
                            "  executing",
                            argv,
                            "bound",
                            (doc or document)["policy"]["limits"][
                                "max_operation_calls"
                            ],
                            flush=True,
                        )
                        return await execute(c, a, {"argv": argv}, remote, authorize)

                    output = root / "dashboard.json"
                    for venv in [False, True]:
                        if venv:
                            interpreter = root / ".venv/bin/python"
                            interpreter.parent.mkdir(parents=True)
                            interpreter.symlink_to(sys.executable)
                        result = await run(["--output", str(output), "--json"])
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            [row["tool"] for row in result["calls"]],
                            ["mathformer_calibration_" + s for s in ORDER],
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        payload = result["outputs"]["dashboard"]
                        self.assertEqual(json.loads(output.read_text()), payload)
                        self.assertEqual(
                            json.loads(result["outputs"]["stdout"]), payload
                        )
                        self.assertEqual(result["outputs"]["exit_code"], 0)
                        self.assertEqual(payload["execution"]["subprocess_count"], 4)
                        self.assertEqual(
                            payload["evaluation_sets"]["curated_regressions"], 11
                        )
                        self.assertTrue(
                            all(
                                m["false_positive"] == m["false_negative"] == 0
                                for m in payload["metrics"].values()
                            )
                        )
                    # Extra grounding code is tolerated by the native suite but
                    # is a false positive for the dashboard's fixed negative label.
                    negative = (
                        root
                        / "MathformerPhysicsLib/Lean/formalphysics_0191/MathformerPhysics.lean"
                    )
                    original_text = negative.read_text()
                    negative.write_text(
                        original_text + "\nabbrev CalibrationFixture : Prop := True\n"
                    )
                    result = await run(["--output", str(output)])
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], 1)
                    self.assertEqual(result["outputs"]["stdout"], "FAIL\n")
                    self.assertFalse(result["outputs"]["dashboard"]["ok"])
                    self.assertEqual(
                        result["outputs"]["dashboard"]["metrics"][
                            "source_drift_or_trivial_grounding"
                        ]["false_positive"],
                        1,
                    )
                    self.assertEqual(
                        json.loads(output.read_text()), result["outputs"]["dashboard"]
                    )
                    old = oracle()
                    configure(old, root)
                    code, stdout, _ = cli(old, ["--output", str(root / "oracle.json")])
                    self.assertEqual((code, stdout), (1, "FAIL\n"))
                    self.assertEqual(
                        stable(json.loads((root / "oracle.json").read_text())),
                        stable(result["outputs"]["dashboard"]),
                    )
                    negative.write_text(original_text)
                    # Missing real input stops in derivation; no later suite or
                    # dashboard is written, and no retry occurs.
                    output.unlink()
                    fixture = (
                        root
                        / "tests/fixtures/physics_lean_adversarial/direct_target_hypothesis.lean"
                    )
                    text = fixture.read_text()
                    fixture.unlink()
                    result = await run(["--output", str(output)])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(output.exists())
                    fixture.write_text(text)
                    # A publication error follows all four suites, without retry.
                    blocker = root / "blocker"
                    blocker.write_text("file")
                    result = await run(["--output", str(blocker / "report.json")])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 7)
                    # Seven is the exact fixed-call bound, with no adaptive loop.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(["--output", str(output)], bounded)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    self.assertFalse(output.exists())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    c, a = compile(timed)

                    async def waiting_authority():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(c, a, {"argv": []}, remote, waiting_authority)
                    result = await run(["--unknown"])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 1)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
