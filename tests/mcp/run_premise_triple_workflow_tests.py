#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native equivalence and real MCP/Lunar/PRISM execution."""

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
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from backends.atp.MathformerATP import vampire as v
from premise_triple_tools import source, ARTIFACT_ROOT
from premise_triple_boundary import compiler
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_atp_premise_guided_triple_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
FIXTURE = ROOT / "tests/mcp/fixtures/premise_triple_boundary.py"
PROFILE = dict(
    statement=source().DEFAULT_STATEMENT,
    budget="medium",
    seconds=3,
    premise_loop=True,
    generate=True,
    minimize=True,
)
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=True,
    write_report=False,
)


def setup(root, mode):
    file = root / "tests/atp/run_premise_guided_triple_inverse.py"
    file.parent.mkdir(parents=True)
    file.write_text("# required native preflight path\n")
    if mode == "preflight":
        file.unlink()
    (root / "fixture-mode").write_text(mode)
    return root / ARTIFACT_ROOT


def clean(value):
    if isinstance(value, dict):
        return {
            k: clean(x)
            for k, x in value.items()
            if k not in ("generated_at", "elapsed_seconds")
        }
    if isinstance(value, list):
        return [clean(x) for x in value]
    return (
        re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+\+00:00", "<time>", value)
        if isinstance(value, str)
        else value
    )


def assets(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(path, (ROOT / path).read_text())
        for path in sorted({r["path"] for r in doc["provenance"]["sources"]} | {SCHEMA})
    ]


def original():
    scope = dict(vars(v))
    exec(
        (ROOT / "tests/mcp/fixtures/premise_triple_original.py.txt").read_text(), scope
    )
    return scope["discover_proof"]


class TripleTests(unittest.TestCase):
    def test_source_equivalence_and_bypass(self):
        for mode in ["success", "lemma_fail", "unproved"]:
            for guided, generate, minimize in [
                (True, True, True),
                (True, False, False),
                (False, True, True),
            ]:
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    output = setup(root, mode)
                    reports, histories = [], []
                    for entry in [original(), v.discover_proof]:
                        shutil.rmtree(output, ignore_errors=True)
                        (root / "artifacts/vampire_atp/compiler.calls.jsonl").unlink(
                            missing_ok=True
                        )
                        with patch.object(v.subprocess, "run", side_effect=compiler):
                            report = entry(
                                PROFILE["statement"],
                                artifact_root=output,
                                runner=v.VampireRunner(binary="fixture-vampire"),
                                time_limit=3,
                                premise_loop=guided,
                                generate_premises=generate,
                                minimize_premises=minimize,
                            )
                        reports.append(clean(report))
                        histories.append(
                            clean(
                                (
                                    root / "artifacts/vampire_atp/compiler.calls.jsonl"
                                ).read_text()
                            )
                        )
                    self.assertEqual(*reports)
                    self.assertEqual(*histories)
                    self.assertEqual(report["attempt_count"], 1)
                    self.assertEqual(report["ok"], mode != "unproved")

    def test_empty_and_finite_native_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup(root, "success")
            runner = v.VampireRunner(binary="fixture-vampire")
            with patch.object(v.subprocess, "run", side_effect=compiler):
                events = list(
                    v.discover_proof_steps(
                        PROFILE["statement"],
                        artifact_root=root / ARTIFACT_ROOT,
                        runner=runner,
                        time_limit=3,
                        premise_loop=True,
                        workflow_stages=True,
                    )
                )
            self.assertEqual([n for n, _ in events].count("lemma_step"), 2)
            self.assertEqual([n for n, _ in events].count("deletion_step"), 6)
            lemmas = [e for n, e in events if n == "lemma_step"]
            self.assertFalse(lemmas[0]["done"])
            self.assertIn("skipped", lemmas[1])
            self.assertTrue(lemmas[1]["done"])
            trials = [e for n, e in events if n == "deletion_step"]
            self.assertEqual([len(e["attempts"]) for e in trials], list(range(1, 7)))
            self.assertEqual(
                [len(e["current_ids"]) for e in trials], [5, 4, 3, 2, 1, 1]
            )
            self.assertEqual(events[-1][0], "carry_candidate")
            self.assertTrue(events[-1][1]["done"])
            empty = v._minimize_premises_steps(
                problem=v.group_triple_inverse_product_problem(),
                premises=[],
                artifact_root=root,
                runner=runner,
                time_limit=3,
                enabled=True,
                workflow_stages=True,
            )
            self.assertEqual(next(empty), ("augment_pack", {"initial_ids": []}))
            self.assertEqual(next(empty), ("deletion_step", {"done": True}))
            self.assertEqual(next(empty)[0], "minimization_finish")
            with self.assertRaises(StopIteration) as done:
                next(empty)
            self.assertEqual(done.exception.value[:2], ([], []))

    def test_native_candidate_exhaustion_and_empty_generation(self):
        # Real built-in subset portfolio supplies two candidates without replacing
        # autoformalization, selection, generation, or any source step.
        statement = "Subset is transitive; subset of T"
        for mode, expected in [("success", 1), ("unproved", 2)]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = setup(root, mode)
                runner = v.VampireRunner(binary="fixture-vampire")
                with patch.object(v.subprocess, "run", side_effect=compiler):
                    steps = v.discover_proof_steps(
                        statement,
                        artifact_root=output,
                        runner=runner,
                        time_limit=3,
                        premise_loop=True,
                        workflow_stages=True,
                    )
                    events = []
                    while True:
                        try:
                            events.append(next(steps))
                        except StopIteration as done:
                            report = done.value
                            break
                self.assertEqual(report["candidate_count"], 2)
                self.assertEqual(report["attempt_count"], expected)
                carries = [e for n, e in events if n == "carry_candidate"]
                self.assertTrue(carries[-1]["done"])
                if expected == 2:
                    self.assertFalse(carries[0]["done"])
                    self.assertIsNone(report["winner"])
                seeds = [e for n, e in events if n == "select_pack"]
                self.assertTrue(all(e["generated_count"] == 0 for e in seeds))
                helpers = [e for n, e in events if n == "lemma_step"]
                self.assertEqual(helpers, [{"done": True}] * expected)
                self.assertTrue(
                    all(
                        a["premise_generation_report"]["generated_count"] == 0
                        for a in report["attempts"]
                    )
                )

    def test_registered_mcp_and_real_prism(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_atp_premise_guided_triple_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(mode, dry=False, exhaust=False, budget=None):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = setup(root, mode)
                manager = SessionManager()
                async with manager.open(
                    "triple",
                    StdioConfig(
                        command=sys.executable,
                        args=[str(FIXTURE), str(root)],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        advertised = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]
                        doc = deepcopy(document)
                        if budget:
                            doc["policy"]["limits"]["max_operation_calls"] = budget
                        if exhaust:
                            # The helper loop must fail after the first, nonterminal proposal.
                            doc["flow"]["steps"][2]["body"]["steps"][2][
                                "max_iterations"
                            ] = 1
                        snapshot = assets(doc)
                        compiled = compile_workflow(
                            "mcp:triple",
                            workflow_documents([DESCRIPTOR], snapshot)[0],
                            advertised,
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
                            dict(context=dict(CONTEXT, dry_run=dry), profile=PROFILE),
                            remote,
                            authorize,
                        )
                        if mode in ["error", "unproved"] or exhaust or budget:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            if exhaust:
                                self.assertEqual(result["failure_disposition"], "fail")
                                self.assertEqual(
                                    len(
                                        (
                                            root
                                            / "artifacts/vampire_atp/compiler.calls.jsonl"
                                        )
                                        .read_text()
                                        .splitlines()
                                    ),
                                    1,
                                )
                            if mode == "error":
                                self.assertEqual(
                                    result["calls"][-1]["operation"], "lemma"
                                )
                                self.assertEqual(
                                    result["calls"][-1]["status"], "rejected"
                                )
                                self.assertFalse(
                                    (output / "discovery_report.json").exists()
                                )
                            return
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        if dry or mode == "preflight":
                            self.assertEqual(payload["ok"], mode != "preflight")
                            self.assertFalse(output.exists())
                            self.assertFalse(
                                (
                                    root / "artifacts/vampire_atp/compiler.calls.jsonl"
                                ).exists()
                            )
                            return
                        self.assertEqual(
                            payload["returncode"], 0 if mode == "success" else 3
                        )
                        self.assertTrue(payload["write_audit"]["ok"], payload)
                        report = json.loads(payload["stdout"])
                        self.assertEqual(report["ok"], mode == "success")
                        self.assertEqual(report["attempt_count"], 1)
                        generation = report["attempts"][0]["premise_generation_report"]
                        self.assertEqual(generation["generated_count"], 2)
                        self.assertEqual(generation["attempted_count"], 1)
                        self.assertEqual(
                            len(generation["promoted_ids"]),
                            1 if mode == "success" else 0,
                        )
                        self.assertEqual(
                            generation["generated_lemmas"][-1]["proof_status"],
                            "rejected",
                        )
                        self.assertEqual(
                            len(report["attempts"][0]["premise_minimization_attempts"]),
                            6 if mode == "success" else 5,
                        )
                        self.assertEqual(
                            report["winning_final_premise_ids"],
                            (
                                ["generated_binary_product_inverse_reverse_order"]
                                if mode == "success"
                                else []
                            ),
                        )
                        calls = [
                            json.loads(line)
                            for line in (
                                root / "artifacts/vampire_atp/compiler.calls.jsonl"
                            )
                            .read_text()
                            .splitlines()
                        ]
                        for call in calls:
                            limit = call["command"][
                                call["command"].index("--time_limit") + 1
                            ]
                            self.assertEqual(
                                limit,
                                (
                                    "1"
                                    if "/premise_minimization/" in call["command"][-1]
                                    else "3"
                                ),
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertNotIn(
                            "test_assertions",
                            json.loads((output / "discovery_report.json").read_text()),
                        )
                        history = clean(
                            (
                                root / "artifacts/vampire_atp/compiler.calls.jsonl"
                            ).read_text()
                        )
                        shutil.rmtree(output)
                        (root / "artifacts/vampire_atp/compiler.calls.jsonl").unlink()
                        with patch.object(v.subprocess, "run", side_effect=compiler):
                            expected = original()(
                                PROFILE["statement"],
                                artifact_root=output,
                                runner=v.VampireRunner(binary="fixture-vampire"),
                                time_limit=3,
                                premise_loop=True,
                            )
                        source().check_report(expected)
                        self.assertEqual(clean(report), clean(expected))
                        self.assertEqual(
                            history,
                            clean(
                                (
                                    root / "artifacts/vampire_atp/compiler.calls.jsonl"
                                ).read_text()
                            ),
                        )
                    except BaseException as error:
                        failure = error
                    else:
                        failure = None
                if failure:
                    raise failure
                self.assertFalse(manager.active)

        for mode, dry, exhaust, budget in [
            ("success", False, False, None),
            ("lemma_fail", False, False, None),
            ("unproved", False, False, None),
            ("error", False, False, None),
            ("success", True, False, None),
            ("preflight", False, False, None),
            ("success", False, True, None),
            ("success", False, False, 2),
        ]:
            asyncio.run(scenario(mode, dry, exhaust, budget))


if __name__ == "__main__":
    unittest.main(verbosity=2)
