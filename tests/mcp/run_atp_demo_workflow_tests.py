#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Source equivalence and registered MCP tools through the real Lunar/PRISM runtime."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]

import asyncio
from copy import deepcopy
import hashlib
import json
import shutil
import re
import tempfile
import unittest
from unittest.mock import patch
import yaml
from backends.atp.MathformerATP import vampire as v
from atp_demo_tools import DEMO
from atp_demo_boundary import compiler
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_atp_demo_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
FIXTURE = ROOT / "tests/mcp/fixtures/atp_demo_boundary.py"


def setup(root, mode="success"):
    (root / "examples").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / DEMO["text_file"], root / DEMO["text_file"])
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts/run_vampire_atp.py").write_text("# fixture preflight path\n")
    (root / "fixture-mode").write_text(mode)
    if mode == "preflight":
        (root / "scripts/run_vampire_atp.py").unlink()
    return root / DEMO["artifact_root"]


def clean(value, root):
    if isinstance(value, dict):
        return {
            k: clean(vv, root)
            for k, vv in value.items()
            if k not in ("generated_at", "elapsed_seconds")
        }
    if isinstance(value, list):
        return [clean(vv, root) for vv in value]
    return (
        re.sub(
            r"\d{4}-\d\d-\d\dT[0-9:.]+\+00:00",
            "<time>",
            value.replace(str(root), "<root>"),
        )
        if isinstance(value, str)
        else value
    )


def assets(document):
    paths = {row["path"] for row in document["provenance"]["sources"]} | {SCHEMA}

    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(path, (ROOT / path).read_text()) for path in sorted(paths)
    ]


def oracle():
    scope = dict(vars(v))
    exec((ROOT / "tests/mcp/fixtures/atp_demo_original.py.txt").read_text(), scope)
    return scope["discover_proof"]


class ATPTests(unittest.TestCase):
    def test_source_equivalence_and_disabled_branches(self):
        original = oracle()
        for mode in ["success", "unproved"]:
            for statement in [
                (ROOT / DEMO["text_file"]).read_text(),
                "Subset is transitive; subset of T",
            ]:
                for premise_loop, generation, minimization in [
                    (True, True, True),
                    (True, False, False),
                    (False, True, True),
                ]:
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        output = setup(root, mode)
                        reports, histories = [], []
                        for entry in [original, v.discover_proof]:
                            shutil.rmtree(output, ignore_errors=True)
                            with patch.object(
                                v.subprocess, "run", side_effect=compiler
                            ):
                                report = entry(
                                    statement,
                                    artifact_root=output,
                                    runner=v.VampireRunner(binary="fixture-vampire"),
                                    time_limit=3,
                                    premise_loop=premise_loop,
                                    premise_budget="medium",
                                    generate_premises=generation,
                                    minimize_premises=minimization,
                                )
                            reports.append(clean(report, root))
                            histories.append(
                                clean(
                                    (output / "compiler.calls.jsonl").read_text(), root
                                )
                            )
                        self.assertEqual(*reports)
                        self.assertEqual(*histories)
                        report = reports[-1]
                        self.assertEqual(report["ok"], mode == "success")
                        self.assertEqual(
                            report["attempt_count"],
                            1 if mode == "success" else report["candidate_count"],
                        )
                        self.assertEqual(
                            report["winner"] is not None, mode == "success"
                        )
                        self.assertTrue((output / "discovery_report.json").exists())

    def test_empty_minimization_and_source_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = setup(root)
            output.mkdir(parents=True)
            problem = v.group_inverse_product_problem()
            runner = v.VampireRunner(binary="fixture-vampire")
            with patch.object(v.subprocess, "run", side_effect=compiler):
                steps = v._minimize_premises_steps(
                    problem=problem,
                    premises=[],
                    artifact_root=output,
                    runner=runner,
                    time_limit=3,
                    enabled=True,
                )
                self.assertEqual(next(steps), ("augment_pack", {"initial_ids": []}))
                self.assertEqual(next(steps), ("deletion_step", {"done": True}))
                with self.assertRaises(StopIteration) as stopped:
                    next(steps)
                self.assertEqual(stopped.exception.value[:2], ([], []))
                self.assertFalse((output / "compiler.calls.jsonl").exists())
                statement = (ROOT / DEMO["text_file"]).read_text()
                steps = v.discover_proof_steps(
                    statement,
                    artifact_root=output,
                    runner=runner,
                    time_limit=3,
                    premise_loop=True,
                )
                events = []
                while True:
                    try:
                        events.append(next(steps))
                    except StopIteration as completed:
                        report = completed.value
                        break
            names = [name for name, _ in events]
            self.assertEqual(names[:2], ["initialize", "select_pack"])
            self.assertEqual(names.count("lemma_step"), 4)
            self.assertEqual(names[-2:], ["final_attempt", "carry_candidate"])
            self.assertEqual(
                sum(bool(e.get("skipped")) for n, e in events if n == "lemma_step"), 1
            )
            selected = events[1][1]["selected_ids"]
            self.assertLessEqual(len(selected), 8)
            augmented = next(e["initial_ids"] for n, e in events if n == "augment_pack")
            self.assertEqual(augmented[: len(selected)], selected)
            trials = [e for n, e in events if n == "deletion_step"]
            self.assertEqual(len(trials), len(augmented))
            self.assertTrue(trials[-1]["done"])
            self.assertFalse(any(t["done"] for t in trials[:-1]))
            self.assertEqual(events[-1][1]["attempt_count"], 1)
            self.assertTrue(events[-1][1]["done"])
            self.assertTrue(report["ok"])

    def test_real_mcp_prism_paths_and_exhaustion(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_atp_demo_workflow")
        self.assertEqual(document["lifecycle"], "active")

        async def scenario(mode, dry=False, allow=True, exhaust=False):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = setup(root, mode)
                manager = SessionManager()
                async with manager.open(
                    "atp",
                    StdioConfig(
                        command=sys.executable,
                        args=[str(FIXTURE), str(root)],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            tool.model_dump(by_alias=True, exclude_none=True)
                            for tool in await remote.tools()
                        ]
                        doc = deepcopy(document)
                        if exhaust:
                            doc["flow"]["steps"][2]["body"]["steps"][1][
                                "max_iterations"
                            ] = 1
                        snapshot = assets(doc)
                        compiled = compile_workflow(
                            "mcp:atp",
                            workflow_documents([DESCRIPTOR], snapshot)[0],
                            tools,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertTrue(compiled["runtime_source"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )

                        async def authorize():
                            pass

                        result = await execute(
                            compiled,
                            snapshot,
                            {
                                "context": dict(
                                    dry_run=dry,
                                    json_output=True,
                                    keep_going=False,
                                    allow_mutating=allow,
                                    write_report=False,
                                ),
                                "demo": DEMO,
                            },
                            remote,
                            authorize,
                        )
                        if mode == "error" or exhaust:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertFalse(
                                (output / "discovery_report.json").exists()
                            )
                            records = (
                                (output / "compiler.calls.jsonl")
                                .read_text()
                                .splitlines()
                            )
                            self.assertEqual(len(records), 1)
                            if exhaust:
                                self.assertEqual(result["failure_disposition"], "fail")
                            return
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        if dry or mode == "preflight":
                            self.assertFalse(output.exists())
                            self.assertEqual(len(result["calls"]), 9)
                            self.assertEqual(payload["ok"], mode != "preflight")
                            if dry and allow:
                                self.assertEqual(payload["status"], "dry_run")
                            return
                        self.assertEqual(
                            payload["returncode"], 3 if mode == "unproved" else 0
                        )
                        self.assertEqual(payload["ok"], mode != "unproved", payload)
                        self.assertEqual(payload["status"], "completed", payload)
                        self.assertTrue(payload["write_audit"]["ok"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        report = json.loads(
                            (output / "discovery_report.json").read_text()
                        )
                        calls = [
                            json.loads(line)
                            for line in (output / "compiler.calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        attempt = report["attempts"][0]
                        attempt["premise_selection_report"]
                        generation = attempt["premise_generation_report"]
                        self.assertEqual(report["candidate_count"], 1)
                        self.assertEqual(report["attempt_count"], 1)
                        self.assertEqual(generation["generated_count"], 4)
                        self.assertEqual(generation["attempted_count"], 3)
                        self.assertLessEqual(len(attempt["final_premise_ids"]), 8 + 3)
                        self.assertTrue(any(c["path"].endswith(".p") for c in calls))
                        lemma_calls = [
                            c for c in calls if "/premise_generation/" in c["path"]
                        ]
                        min_calls = [
                            c for c in calls if "/premise_minimization/" in c["path"]
                        ]
                        self.assertEqual(len(lemma_calls), 3)
                        self.assertEqual(
                            len(min_calls),
                            len(attempt["premise_minimization_attempts"]),
                        )
                        self.assertTrue(
                            all(
                                c["command"][c["command"].index("--time_limit") + 1]
                                == "1"
                                for c in min_calls
                            )
                        )
                        self.assertTrue(
                            all(
                                c["command"][c["command"].index("--time_limit") + 1]
                                == "3"
                                for c in lemma_calls
                            )
                        )
                        self.assertTrue(
                            any(
                                t["ok_without_premise"]
                                for t in attempt["premise_minimization_attempts"]
                            )
                        )
                        self.assertTrue(
                            any(
                                t["kept"]
                                for t in attempt["premise_minimization_attempts"]
                            )
                        )
                        # Compare the complete native report and compiler history to the frozen entrypoint.
                        actual = clean(report, root)
                        actual_calls = clean(calls, root)
                        shutil.rmtree(output)
                        with patch.object(v.subprocess, "run", side_effect=compiler):
                            expected = oracle()(
                                (ROOT / DEMO["text_file"]).read_text(),
                                artifact_root=output,
                                runner=v.VampireRunner(binary="fixture-vampire"),
                                time_limit=3,
                                premise_loop=True,
                                premise_budget="medium",
                            )
                        self.assertEqual(actual, clean(expected, root))
                        expected_calls = [
                            json.loads(line)
                            for line in (output / "compiler.calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        self.assertEqual(actual_calls, clean(expected_calls, root))
                    except BaseException as error:
                        import traceback

                        traceback.print_exc()
                        failure = error
                    else:
                        failure = None
                if failure:
                    raise failure
                self.assertFalse(manager.active)

        for mode, dry, allow, exhaust in [
            ("success", False, True, False),
            ("unproved", False, True, False),
            ("success", True, True, False),
            ("success", False, False, False),
            ("preflight", False, True, False),
            ("error", False, True, False),
            ("success", False, True, True),
        ]:
            asyncio.run(scenario(mode, dry, allow, exhaust))


if __name__ == "__main__":
    unittest.main(verbosity=2)
