#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real source, MCP transport and Lunar PRISM compilation/execution fixtures.

There are no external model/provider/compiler calls in this workflow. Fixtures
are isolated repository mounts and JSON inputs, never simulated production
steps. PRISM parser/checker/compiler/runtime are real, with no substitutions.
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
from contextlib import redirect_stdout, redirect_stderr
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
import mathformer as hub
from paper_update_plan_tools import source, PLANNER, EVIDENCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_update_plan_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/paper-update-plan.workflow.json"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)
PACKET = "artifacts/paper_skills/new_functionality_evidence_packet.json"
OUTPUT = "artifacts/paper_skills/paper_update_plan.md"


def oracle(root=ROOT):
    path = ROOT / "tests/mcp/fixtures/paper_update_plan_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "paper_update_original", SourceFileLoader("paper_update_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    return module


def mount(root, *, evidence=True, planner=True):
    # Real copies, not executable stubs; their existence drives native preflight.
    for path, enabled in [(EVIDENCE, evidence), (PLANNER, planner)]:
        if enabled:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
    return root


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {r["path"] for r in document["provenance"]["sources"]} | {SCHEMA}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


def invoke(module, argv):
    stream = io.StringIO()
    with patch.object(sys, "argv", ["planner", *argv]), redirect_stdout(stream):
        code = module.main()
    return code, stream.getvalue()


class PaperUpdateTests(unittest.TestCase):
    def test_contract_source_and_generator(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        result = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["id"], "hub_paper_update_plan_workflow")
        self.assertIn(PLANNER, [r["path"] for r in document["provenance"]["sources"]])
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("paper_update_normalizer", path)
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(x for x in normalizer.inventory() if x["id"] == document["id"]),
            document,
        )
        registry = hub.build_registry()
        self.assertEqual(
            registry["paper:update-plan"].depends_on, ("paper:evidence-packet",)
        )
        self.assertIsNone(registry["paper:update-plan"].timeout_seconds)
        self.assertIsNone(registry["paper:evidence-packet"].timeout_seconds)
        # No action/test entrypoint audit bypass; these belong to the tool family.
        audit = hub.audit_control(registry)
        for path in [
            "scripts/paper_update_plan_tools.py",
            "tests/mcp/run_paper_update_plan_workflow_tests.py",
        ]:
            self.assertNotIn(path, audit["uncontrolled_entrypoints"])
        import mathformer_mcp_service

        report = mathformer_mcp_service.service_coverage_report(Path("unused"))
        for step in document["operations"]:
            self.assertIn("mathformer_paper_update_" + step, report["mcp_tools"])
        self.assertIn(
            "register_paper_update_plan_tools(mcp,",
            (ROOT / "scripts/mcp_server.py").read_text(),
        )

    def test_native_original_equivalence_and_exhaustion(self):
        native, original = source(), oracle()
        features = [
            {
                "feature_name": "A",
                "feature_summary": "fixture",
                "supported_paper_claims": [
                    "first",
                    {"claim": "second", "path": "ignored"},
                    {"path": "path"},
                    {"z": 1, "a": 2},
                    "first",
                ],
                "target_paper_sections": ["Methods"],
                "explicit_non_claims": ["no proof"],
                "figure_table_implications": ["Table 1"],
                "limitations_and_blockers": ["risk"],
            },
            {
                "feature_id": "B",
                "supported_paper_claims": ["second", "third"],
                "target_paper_sections": ["Methods", "Results"],
            },
        ]
        for packet in [
            features[0],
            {"features": features},
            {"features": []},
            {},
            {"features": [features[0]] * 1031},
        ]:
            plan = native.build_plan(packet)
            self.assertEqual(plan, original.build_plan(packet))
            self.assertEqual(native.markdown_plan(plan), original.markdown_plan(plan))
        plan = native.build_plan({"features": features})
        self.assertEqual(
            plan["paper_claim_delta"],
            ["first", "second", "path", '{"a": 2, "z": 1}', "third"],
        )
        self.assertEqual(plan["section_patch_plan"], ["Methods", "Results"])
        self.assertEqual(plan["features"][1]["feature_name"], "unknown")
        self.assertIn("- None recorded.", native.markdown_plan(native.build_plan({})))
        # Preserve native membership-before-string-conversion behavior exactly.
        self.assertEqual(native.collect_unique([{"v": [1, 1, "1"]}], "v"), ["1", "1"])
        for packet in [
            None,
            {"features": None},
            {"features": [3]},
            {"supported_paper_claims": [[]]},
            {"features": [{"supported_paper_claims": None}]},
        ]:
            for module in [native, original]:
                with self.assertRaises((TypeError, AttributeError)):
                    module.build_plan(packet)
        for argv, code in [(["--help"], 0), (["--bad"], 2)]:
            with (
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                native.parse_options(argv)
            self.assertEqual(error.exception.code, code)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old, current = oracle(root), source(repository_root=root)
            (root / "packet.json").write_text(json.dumps({"features": features}))
            for json_mode in [False, True]:
                argv = [
                    "--evidence-packet",
                    "packet.json",
                    "--output",
                    "nested/plan.md",
                ] + (["--json"] if json_mode else [])
                expected = invoke(old, argv)
                markdown = (root / "nested/plan.md").read_bytes()
                companion = (root / "nested/plan.json").read_bytes()
                self.assertEqual(invoke(current, argv), expected)
                self.assertEqual((root / "nested/plan.md").read_bytes(), markdown)
                self.assertEqual((root / "nested/plan.json").read_bytes(), companion)
                self.assertEqual(
                    companion.decode(),
                    json.dumps(plan, indent=2, sort_keys=True) + "\n",
                )
            for name in ["absent.json", "bad.json"]:
                if name == "bad.json":
                    (root / name).write_text("{")
                for module in [old, current]:
                    with self.assertRaises((FileNotFoundError, json.JSONDecodeError)):
                        invoke(module, ["--evidence-packet", name])

    def test_native_hub_stopping(self):
        registry = hub.build_registry()
        context = hub.RunContext(**{**CONTEXT, "dry_run": True})
        for action, extra, seen, status in [
            ("unknown", [], [], "unknown_action"),
            ("paper:update-plan", [], ["paper:update-plan"], "dependency_cycle"),
            ("paper:update-plan", ["--help"], [], "extra_args_for_sequence"),
        ]:
            result = hub.run_action(
                action, registry, context, extra_args=extra, seen=set(seen)
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], status)
        result = hub.run_action("paper:update-plan", registry, context)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["children"]), 1)
        self.assertEqual(result["children"][0]["status"], "dry_run")
        self.assertEqual(result["leaf"]["status"], "dry_run")

    def test_real_mcp_lunar_compile_execute(self):
        asyncio.run(self.runtime())

    async def runtime(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        manager = SessionManager()
        with tempfile.TemporaryDirectory(prefix="paper-update-fixtures-") as temp:
            base = Path(temp)
            # Each mount exercises the actual source/registry; none is a provider mock.
            roots = {
                name: mount(
                    base / name,
                    evidence=name not in ["dependency", "load", "build"],
                    planner=name != "preflight",
                )
                for name in [
                    "success",
                    "dry",
                    "cycle",
                    "extra",
                    "dependency",
                    "load",
                    "build",
                    "preflight",
                    "publish",
                    "partial",
                    "budget",
                    "audit",
                    "evidence_io",
                ]
            }
            packet = roots["load"] / PACKET
            packet.parent.mkdir(parents=True)
            packet.write_text("{")
            packet = roots["build"] / PACKET
            packet.parent.mkdir(parents=True)
            packet.write_text('{"features":[3]}')
            (roots["evidence_io"] / PACKET).mkdir(parents=True)
            (roots["publish"] / OUTPUT).mkdir(parents=True)
            (roots["partial"] / Path(OUTPUT).with_suffix(".json")).mkdir(parents=True)
            command = ["scripts/paper_update_plan_tools.py"]
            for root in roots.values():
                command += ["--mount-root", str(root)]
            failure = None
            async with manager.open(
                "paper-update",
                StdioConfig(command=sys.executable, args=command, cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        result = compile_workflow(
                            "mcp:paper-update",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return result, assets

                    workflow, assets = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    for operation in document["operations"].values():
                        target = operation["execution"]["binding"]["target"]
                        self.assertFalse(
                            compile(
                                document, [t for t in tools if t["name"] != target]
                            )[0]["runnable"]
                        )

                    async def authorize():
                        pass

                    async def run(name, context=None, extra=None, seen=None, doc=None):
                        selected, received = compile(doc) if doc else (workflow, assets)
                        return await execute(
                            selected,
                            received,
                            dict(
                                context={**CONTEXT, **(context or {})},
                                repository_root=str(roots[name]),
                                extra_args=extra or [],
                                seen=seen or [],
                            ),
                            remote,
                            authorize,
                        )

                    result = await run("success")
                    self.assertEqual(result["status"], "accepted", result)
                    output = result["outputs"]["result"]
                    self.assertTrue(output["ok"], output)
                    self.assertEqual(output["status"], "completed_with_dependencies")
                    self.assertEqual(len(output["children"]), 1)
                    self.assertEqual(
                        output["children"][0]["action"]["id"], "paper:evidence-packet"
                    )
                    self.assertTrue(output["children"][0]["ok"])
                    expected_packet = source(EVIDENCE, roots["success"]).build_packet(
                        "all"
                    )
                    self.assertEqual(
                        json.loads((roots["success"] / PACKET).read_text()),
                        expected_packet,
                    )
                    expected_plan = oracle().build_plan(expected_packet)
                    self.assertEqual(
                        json.loads(
                            (
                                roots["success"] / Path(OUTPUT).with_suffix(".json")
                            ).read_text()
                        ),
                        expected_plan,
                    )
                    self.assertEqual(
                        (roots["success"] / OUTPUT).read_text(),
                        oracle().markdown_plan(expected_plan),
                    )
                    self.assertEqual(expected_plan["feature_count"], 4)
                    self.assertEqual(
                        json.loads(output["leaf"]["stdout"])["feature_count"], 4
                    )
                    self.assertEqual(output["leaf"]["returncode"], 0)
                    self.assertTrue(output["leaf"]["write_audit"]["ok"])
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_paper_update_" + s
                            for s in ["prepare", "load", "build", "publish", "finish"]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    # Result-data failure remains a successful transport invocation;
                    # hub ok never changes into scientific validation/acceptance.
                    cases = [
                        (
                            "dry",
                            {"dry_run": True},
                            None,
                            None,
                            "completed_with_dependencies",
                            True,
                            2,
                        ),
                        (
                            "cycle",
                            {},
                            None,
                            ["paper:update-plan"],
                            "dependency_cycle",
                            False,
                            2,
                        ),
                        (
                            "extra",
                            {},
                            ["--help"],
                            None,
                            "extra_args_for_sequence",
                            False,
                            2,
                        ),
                        ("dependency", {}, None, None, "sequence_failed", False, 2),
                        ("evidence_io", {}, None, None, "sequence_failed", False, 2),
                        (
                            "preflight",
                            {},
                            None,
                            None,
                            "failed_with_dependencies",
                            False,
                            2,
                        ),
                        (
                            "load",
                            {"keep_going": True},
                            None,
                            None,
                            "failed_with_dependencies",
                            False,
                            3,
                        ),
                        (
                            "build",
                            {"keep_going": True},
                            None,
                            None,
                            "failed_with_dependencies",
                            False,
                            4,
                        ),
                        (
                            "publish",
                            {},
                            None,
                            None,
                            "failed_with_dependencies",
                            False,
                            5,
                        ),
                        (
                            "partial",
                            {},
                            None,
                            None,
                            "failed_with_dependencies",
                            False,
                            5,
                        ),
                    ]
                    for name, context, extra, seen, status, ok, calls in cases:
                        response = await run(name, context, extra, seen)
                        self.assertEqual(response["status"], "accepted", response)
                        data = response["outputs"]["result"]
                        self.assertEqual(
                            (data["status"], data["ok"]), (status, ok), (name, data)
                        )
                        self.assertEqual(len(response["calls"]), calls, name)
                        if name in [
                            "dry",
                            "cycle",
                            "extra",
                            "dependency",
                            "load",
                            "build",
                        ]:
                            self.assertFalse((roots[name] / OUTPUT).exists())
                        if name in ["load", "build", "publish", "partial"]:
                            self.assertEqual(data["leaf"]["returncode"], 1)
                            self.assertTrue(data["leaf"]["stderr"])
                            self.assertTrue(data["leaf"]["write_audit"]["ok"])
                        if name == "evidence_io":
                            self.assertEqual(data["children"][0]["returncode"], 1)
                            self.assertIn(
                                "IsADirectoryError", data["children"][0]["stderr"]
                            )
                            self.assertTrue(data["children"][0]["write_audit"]["ok"])
                        if name == "preflight":
                            self.assertTrue(data["children"][0]["ok"])
                            self.assertTrue(data["leaf"]["preflight_errors"])
                        if name == "partial":
                            self.assertTrue((roots[name] / OUTPUT).is_file())
                            self.assertIn("IsADirectoryError", data["leaf"]["stderr"])
                    # keep-going uses a real stale packet after dependency preflight
                    # failure: successful parent cannot recover dependency ok.
                    missing = await run("dependency", {"keep_going": True})
                    self.assertEqual(len(missing["calls"]), 3)
                    self.assertIn(
                        "FileNotFoundError",
                        missing["outputs"]["result"]["leaf"]["stderr"],
                    )
                    root = roots["dependency"]
                    stale = root / PACKET
                    stale.parent.mkdir(parents=True, exist_ok=True)
                    stale.write_text('{"features":[]}')
                    response = await run("dependency", {"keep_going": True})
                    data = response["outputs"]["result"]
                    self.assertFalse(data["ok"])
                    self.assertTrue(data["leaf"]["ok"])
                    self.assertEqual(data["status"], "failed_with_dependencies")
                    self.assertEqual(
                        json.loads(
                            (root / Path(OUTPUT).with_suffix(".json")).read_text()
                        )["feature_count"],
                        0,
                    )
                    self.assertIn("- None recorded.", (root / OUTPUT).read_text())
                    # Single-feature and large collections exhaust native traversal
                    # inside the real bound build tool, without an invented cap.
                    for packet, count in [
                        ({"feature_name": "standalone"}, 1),
                        (
                            {"features": [{"supported_paper_claims": ["same"]}] * 1031},
                            1031,
                        ),
                    ]:
                        stale.write_text(json.dumps(packet))
                        response = await run("dependency", {"keep_going": True})
                        self.assertEqual(response["status"], "accepted", response)
                        self.assertTrue(response["outputs"]["result"]["leaf"]["ok"])
                        actual = json.loads(
                            (root / Path(OUTPUT).with_suffix(".json")).read_text()
                        )
                        self.assertEqual(actual, oracle().build_plan(packet))
                        self.assertEqual(actual["feature_count"], count)
                        self.assertEqual(len(response["calls"]), 5)
                    # Runtime budgets are separate from uncapped native data loops.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 3
                    response = await run("budget", doc=bounded)
                    self.assertEqual(response["status"], "failed", response)
                    self.assertIn("budget", str(response).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in response["calls"]
                        ),
                        3,
                    )
                    self.assertFalse((roots["budget"] / OUTPUT).exists())
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    selected, received = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            selected,
                            received,
                            dict(
                                context=CONTEXT,
                                repository_root=str(roots["budget"]),
                                extra_args=[],
                                seen=[],
                            ),
                            remote,
                            pending,
                        )
                    # Test audit on the actual before/after snapshots, including a
                    # nonzero completed stage; unexpected writes override status.
                    prepared = await remote.call(
                        "mathformer_paper_update_prepare",
                        dict(
                            context=CONTEXT,
                            repository_root=str(roots["audit"]),
                            extra_args=[],
                            seen=[],
                        ),
                    )
                    boundary = prepared["boundary"]
                    loaded = await remote.call(
                        "mathformer_paper_update_load", {"boundary": boundary}
                    )
                    built = await remote.call(
                        "mathformer_paper_update_build", {"loaded": loaded["loaded"]}
                    )
                    written = await remote.call(
                        "mathformer_paper_update_publish",
                        {"loaded": loaded["loaded"], "plan": built["plan"]},
                    )
                    (roots["audit"] / "unexpected.txt").write_text(
                        "fixture audit change"
                    )
                    finished = await remote.call(
                        "mathformer_paper_update_finish",
                        {"boundary": boundary, "process": written["process"]},
                    )
                    self.assertFalse(finished["result"]["ok"])
                    self.assertEqual(
                        finished["result"]["leaf"]["status"], "undeclared_writes"
                    )
                    self.assertIn(
                        "unexpected.txt",
                        finished["result"]["leaf"]["write_audit"]["unexpected_paths"],
                    )
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_paper_update_finish", {"boundary": boundary}
                        )
                    with self.assertRaises(Exception):
                        await remote.call(
                            "mathformer_paper_update_prepare",
                            dict(
                                context=CONTEXT,
                                repository_root=str(base),
                                extra_args=[],
                                seen=[],
                            ),
                        )
                    # Registered load also retains native argparse termination.
                    bad = deepcopy(boundary)
                    bad["leaf"]["payload"]["argv"] += ["--bad"]
                    loaded = await remote.call(
                        "mathformer_paper_update_load", {"boundary": bad}
                    )
                    self.assertFalse(loaded["loaded_ok"])
                    self.assertEqual(set(loaded["loaded"]), {"process"})
                    self.assertEqual(loaded["process"]["returncode"], 2)
                    bad["leaf"]["payload"]["argv"] = bad["leaf"]["payload"]["argv"][
                        :2
                    ] + ["--help"]
                    loaded = await remote.call(
                        "mathformer_paper_update_load", {"boundary": bad}
                    )
                    self.assertFalse(loaded["loaded_ok"])
                    self.assertEqual(loaded["process"]["returncode"], 0)
                    self.assertIn("--evidence-packet", loaded["process"]["stdout"])
                except Exception as error:
                    failure = error
            if failure:
                raise failure
            async with manager.open(
                "readonly",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        "scripts/paper_update_plan_tools.py",
                        "--readonly",
                        "--mount-root",
                        str(roots["audit"]),
                    ],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                with self.assertRaises(Exception):
                    await remote.call(
                        "mathformer_paper_update_prepare",
                        dict(
                            context=CONTEXT,
                            repository_root=str(roots["audit"]),
                            extra_args=[],
                            seen=[],
                        ),
                    )
                prepared = await remote.call(
                    "mathformer_paper_update_prepare",
                    dict(
                        context={**CONTEXT, "dry_run": True},
                        repository_root=str(roots["audit"]),
                        extra_args=[],
                        seen=[],
                    ),
                )
                self.assertFalse(prepared["execute"])
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
