#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic fixture scans through native, MCP and real Lunar/PRISM runtime.

This audit has no provider or external compiler boundary. No substitutions are
needed: PRISM parsing, checking, compilation and execution all run for real.
"""

# ruff: noqa: E402 - imports follow interpreter and source path setup
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from skill_coverage_tools import source, SOURCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_skill_coverage_workflow/workflow.yaml"
INPUTS = dict(
    hooks_file="skills/SKILL_HOOKS.yaml",
    skills_dir="skills",
    min_non_wrapper_coverage=1.0,
    min_loop_count=6,
)
RUNTIMES = [
    "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py",
    SOURCE,
    "skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py",
]


def oracle():
    source()  # Initialize the original inventory and reasoning helper paths.
    path = ROOT / "tests/mcp/fixtures/skill_coverage_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "skill_coverage_oracle", SourceFileLoader("skill_coverage_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(root, mode):
    skills = root / "skills"
    skills.mkdir()
    if mode != "empty":
        for name, desc in [
            ("a", "owned"),
            ("b", "routed"),
            ("c", "compatibility wrapper"),
            ("d", "normal"),
            ("autoformalization-agentc", "default exemption"),
        ]:
            if mode == "good" and name == "d":
                continue
            p = skills / "theme" / name / "SKILL.md"
            p.parent.mkdir(parents=True)
            p.write_text(f"---\nname: {name}\ndescription: {desc}\n---\n")
    hooks = """hooks:
  - id: good_loop
    owner_skill: a
    reasoning_log_steps:
      - task_start
      - task_ready
  - id: empty_loop
    owner_skill: a
  - id: incomplete_review
    owner_skill: a
    reasoning_log_steps:
      - task_start
  - id: ordinary
    owner_skill: a
    reasoning_log_steps:
      - one_step
"""
    loops = "loop_contracts:\n"
    if mode != "empty":
        for i in range(6 if mode == "good" else 2):
            loops += f"  - id: loop{i}\n    required_hooks:\n      - good_loop\n"
            if mode == "bad":
                loops += "      - absent\n      - empty_loop\n      - incomplete_review\n      - ordinary\n    recommended_hooks:\n      - absent_recommended\n    required_owner_skills:\n      - absent_owner\n"
    runtimes = "runtime_contract:\n  shared_runtime_scripts:\n"
    for path in RUNTIMES if mode != "bad" else RUNTIMES[:-1]:
        runtimes += "    - " + path + "\n"
    (skills / "SKILL_HOOKS.yaml").write_text(
        runtimes + hooks + loops + "direct_request_routing:\n  request: b\n"
    )
    return skills


def audit(module, root):
    return module.audit_skill_coverage(
        hooks_file=root / INPUTS["hooks_file"],
        skills_dir=root / "skills",
        min_non_wrapper_coverage=1.0,
        min_loop_count=6,
    )


def stable(report):
    report = deepcopy(report)
    report.pop("generated_at_utc")
    return report


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in {r["path"]: r for r in document["provenance"]["sources"]}.values()
    ]


class SkillCoverageTests(unittest.TestCase):
    def test_native_steps_cli_and_oracle(self):
        for mode in ("good", "bad", "empty"):
            with tempfile.TemporaryDirectory(
                dir=ROOT, prefix="skill-coverage-fixture-"
            ) as tmp:
                root = Path(tmp)
                fixture(root, mode)
                original = oracle()
                expected = audit(original, root)
                self.assertEqual(stable(audit(source(), root)), stable(expected))
                self.assertEqual(expected["ok"], mode == "good")
                state = source().load_audit(
                    hooks_file=root / INPUTS["hooks_file"],
                    skills_dir=root / "skills",
                    min_non_wrapper_coverage=1.0,
                    min_loop_count=6,
                )
                self.assertEqual(state["cursor"], 0)
                self.assertEqual(state["findings"], [])
                visited = []
                while state["more"]:
                    visited.append(state["skills"][state["cursor"]]["name"])
                    source().classify_one(state)
                    self.assertEqual(state["cursor"], len(visited))
                self.assertEqual(visited, sorted(visited))
                self.assertEqual(
                    state["wrappers"],
                    [] if mode == "empty" else ["autoformalization-agentc", "c"],
                )
                source().thresholds_and_pack(state)
                self.assertEqual(
                    state["coverage_ratio"], 2 / 3 if mode == "bad" else 1.0
                )
                seen = 0
                while state["more"]:
                    source().inspect_contract(state)
                    seen += 1
                self.assertEqual(
                    seen, 6 if mode == "good" else 2 if mode == "bad" else 0
                )
                self.assertEqual(
                    stable(source().finalize_audit(state)), stable(expected)
                )
                codes = [f["code"] for f in expected["findings"]]
                if mode == "bad":
                    self.assertEqual(
                        codes[:4],
                        [
                            "wrapper_without_hook_or_route",
                            "wrapper_without_hook_or_route",
                            "uncovered_skill",
                            "coverage_ratio_below_policy",
                        ],
                    )
                    self.assertEqual(
                        codes[5:10],
                        [
                            "loop_missing_required_hooks",
                            "loop_missing_recommended_hooks",
                            "loop_missing_required_owner_skills",
                            "loop_hook_without_reasoning_steps",
                            "loop_hook_missing_start_complete_pair",
                        ],
                    )
                    self.assertEqual(codes[-1], "missing_required_control_runtime")
                    self.assertEqual(
                        codes.count("loop_hook_missing_start_complete_pair"), 2
                    )
                if mode == "good":
                    self.assertTrue(expected["ok"])  # low findings are nonblocking
                    self.assertEqual(
                        expected["summary"]["severity_counts"],
                        dict(high=0, medium=0, low=2),
                    )
                for flags, failure_code in (([], 3), (["--expect-ok"], 4)):
                    observed = []
                    for module in (original, source()):
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = module.main(
                                [
                                    "--hooks-file",
                                    str(root / INPUTS["hooks_file"]),
                                    "--skills-dir",
                                    str(root / "skills"),
                                    "--json",
                                    *flags,
                                ]
                            )
                        report = json.loads(stream.getvalue())
                        observed.append((code, stable(report)))
                    self.assertEqual(*observed)
                    self.assertEqual(
                        observed[0][0], 0 if mode == "good" else failure_code
                    )

    def test_lunar_registered_tools_and_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "skill-coverage",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:skill-coverage",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return workflow, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(root, doc=None):
                    w, a = compile(doc) if doc else (workflow, assets)
                    return await execute(
                        w,
                        a,
                        {"source": INPUTS, "repo_root": str(root)},
                        remote,
                        authorize,
                    )

                for mode in ("good", "bad", "empty"):
                    with tempfile.TemporaryDirectory(
                        dir=ROOT, prefix="skill-coverage-fixture-"
                    ) as tmp:
                        root = Path(tmp)
                        fixture(root, mode)
                        expected = audit(oracle(), root)
                        result = await run(root)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(
                            stable(result["outputs"]["report"]), stable(expected)
                        )
                        n = expected["summary"]["skill_count"]
                        k = expected["summary"]["loop_contract_count"]
                        self.assertEqual(
                            len(result["calls"]), 3 + max(n, 1) + max(k, 1)
                        )
                        self.assertEqual(
                            result["calls"][0]["tool"],
                            "mathformer_skill_coverage_load_and_pack",
                        )
                        self.assertEqual(
                            result["calls"][-1]["tool"],
                            "mathformer_skill_coverage_finalize",
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        if mode != "empty":
                            bounded = deepcopy(document)
                            for i, cap in ((1, n), (3, k)):
                                bounded["flow"]["steps"][i]["max_iterations"] = cap
                            accepted = await run(root, bounded)
                            self.assertEqual(accepted["status"], "accepted", accepted)
                            self.assertEqual(
                                stable(accepted["outputs"]["report"]), stable(expected)
                            )
                            for i, cap in ((1, n), (3, k)):
                                exhausted = deepcopy(bounded)
                                exhausted["flow"]["steps"][i]["max_iterations"] = (
                                    cap - 1
                                )
                                failed = await run(root, exhausted)
                                self.assertEqual(failed["status"], "failed", failed)
                                self.assertIsNone(failed["outputs"])
                                self.assertEqual(failed["failure_disposition"], "fail")
                                last = "classify_one" if i == 1 else "inspect_contract"
                                self.assertEqual(
                                    failed["calls"][-1]["tool"],
                                    "mathformer_skill_coverage_" + last,
                                )
                            budget = deepcopy(document)
                            budget["policy"]["limits"]["max_operation_calls"] = 2
                            failed = await run(root, budget)
                            self.assertEqual(failed["status"], "failed", failed)
                            self.assertEqual(
                                sum(
                                    bool(c.get("transport_call_performed"))
                                    for c in failed["calls"]
                                ),
                                2,
                            )
                            (root / "skills/theme/a/SKILL.md").write_bytes(b"\xff")
                            with self.assertRaises(UnicodeDecodeError):
                                audit(oracle(), root)
                            failed = await run(root)
                            self.assertEqual(failed["status"], "failed", failed)
                            self.assertIsNone(failed["outputs"])
                            self.assertEqual(len(failed["calls"]), 1)
                with tempfile.TemporaryDirectory(
                    dir=ROOT, prefix="skill-coverage-fixture-"
                ) as tmp:
                    failed = await run(Path(tmp))
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(len(failed["calls"]), 1)
                # Descriptor cardinality admission is distinct from native traversal.
                with tempfile.TemporaryDirectory(
                    dir=ROOT, prefix="skill-coverage-fixture-"
                ) as tmp:
                    root = Path(tmp)
                    fixture(root, "empty")
                    manifest = root / INPUTS["hooks_file"]
                    manifest.write_text(
                        "loop_contracts:\n"
                        + "".join(f"  - id: loop{i}\n" for i in range(10001))
                    )
                    native = source().load_audit(
                        hooks_file=manifest,
                        skills_dir=root / "skills",
                        min_non_wrapper_coverage=1.0,
                        min_loop_count=6,
                    )
                    self.assertEqual(len(native["contracts"]), 10001)
                    failed = await run(root)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), 1)
            except Exception as error:
                import traceback

                traceback.print_exc()
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
