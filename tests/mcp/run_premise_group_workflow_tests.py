#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native regression equivalence and real registered MCP/Lunar/PRISM execution."""

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
import contextlib
from copy import deepcopy
import hashlib
import io
import json
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from premise_group_tools import source
from premise_group_boundary import compiler
from backends.atp.MathformerATP import vampire as v
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_atp_premise_guided_group_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
FIXTURE = ROOT / "tests/mcp/fixtures/premise_group_boundary.py"


def assets(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


def clean(value):
    if isinstance(value, dict):
        return {
            k: clean(vv)
            for k, vv in value.items()
            if k not in ("generated_at", "elapsed_seconds")
        }
    if isinstance(value, list):
        return [clean(vv) for vv in value]
    return (
        re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+\+00:00", "<time>", value)
        if isinstance(value, str)
        else value
    )


def oracle():
    scope = {
        "__file__": str(ROOT / "tests/atp/run_premise_guided_group_inverse.py"),
        "__name__": "original_group_regression",
    }
    exec((ROOT / "tests/mcp/fixtures/premise_group_original.py.txt").read_text(), scope)
    return scope["main"]


class GroupTests(unittest.TestCase):
    def test_cli_original_equivalence(self):
        for mode in ["success", "lemma_fail", "unproved", "error"]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "fixture-mode").write_text(mode)
                results = []
                histories = []
                for main in [oracle(), source().main]:
                    shutil.rmtree(root / "output", ignore_errors=True)
                    (root / "calls.jsonl").unlink(missing_ok=True)
                    out = io.StringIO()
                    with (
                        patch.dict(os.environ, {"VAMPIRE_BIN": "fixture-vampire"}),
                        patch.object(v.subprocess, "run", side_effect=compiler),
                        patch.object(
                            sys,
                            "argv",
                            [
                                "group",
                                "--artifact-root",
                                str(root / "output"),
                                "--json",
                            ],
                        ),
                        contextlib.redirect_stdout(out),
                    ):
                        try:
                            code = main()
                            results.append((code, clean(json.loads(out.getvalue()))))
                        except (TypeError, RuntimeError) as error:
                            results.append((type(error).__name__, str(error)))
                    histories.append((root / "calls.jsonl").read_text())
                self.assertEqual(*results)
                self.assertEqual(*[clean(h) for h in histories])
                self.assertEqual(
                    results[0][0],
                    {
                        "success": 0,
                        "lemma_fail": 3,
                        "unproved": "TypeError",
                        "error": "RuntimeError",
                    }[mode],
                )
        request = source().resolve_request({})
        self.assertEqual(request["time_limit"], 3)
        self.assertTrue(request["premise_loop"])
        self.assertFalse(request["json"])
        self.assertTrue(Path(request["artifact_root"]).is_absolute())
        with (
            patch.object(sys, "argv", ["group", "--invalid"]),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit):
                source().main()

    def test_finite_native_traversals_and_empty_minimization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture-mode").write_text("success")
            runner = v.VampireRunner(binary="fixture-vampire")
            steps = v.discover_proof_steps(
                source().DEFAULT_STATEMENT,
                artifact_root=root / "output",
                runner=runner,
                time_limit=3,
                premise_loop=True,
            )
            events = []
            with patch.object(v.subprocess, "run", side_effect=compiler):
                while True:
                    try:
                        events.append(next(steps))
                    except StopIteration as done:
                        report = done.value
                        break
            self.assertEqual(events[0], ("initialize", {"candidate_count": 1}))
            self.assertEqual(report["attempt_count"], 1)
            lemmas = [e for n, e in events if n == "lemma_step"]
            self.assertEqual(len(lemmas), 4)
            self.assertEqual(sum("skipped" in e for e in lemmas), 1)
            self.assertTrue(lemmas[-1]["done"])
            deletions = [e for n, e in events if n == "deletion_step"]
            self.assertEqual(len(deletions), 8)
            self.assertEqual([len(e["attempts"]) for e in deletions], list(range(1, 9)))
            self.assertEqual(
                [len(e["current_ids"]) for e in deletions], [7, 6, 5, 4, 3, 3, 3, 3]
            )
            self.assertTrue(deletions[-1]["done"])
            self.assertFalse(any(e["done"] for e in deletions[:-1]))
            self.assertEqual(events[-1][0], "carry_candidate")
            self.assertTrue(events[-1][1]["done"])
            empty = v._minimize_premises_steps(
                problem=v.group_inverse_product_problem(),
                premises=[],
                artifact_root=root,
                runner=runner,
                time_limit=3,
                enabled=True,
            )
            self.assertEqual(next(empty), ("augment_pack", {"initial_ids": []}))
            self.assertEqual(next(empty), ("deletion_step", {"done": True}))
            with self.assertRaises(StopIteration) as done:
                next(empty)
            self.assertEqual(done.exception.value[:2], ([], []))
            request = source().resolve_request(
                {"artifact_root": str(root), "json": False}
            )
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(source().emit_report(request, report, 0), 0)
            self.assertEqual(out.getvalue().splitlines()[0], "ok: True")
            self.assertEqual(len(out.getvalue().splitlines()), 6)

    def test_real_registered_tools_and_lunar(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc["id"], "hub_atp_premise_guided_group_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(mode, budget=4):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "fixture-mode").write_text(mode)
                manager = SessionManager()
                async with manager.open(
                    "group",
                    StdioConfig(
                        command=sys.executable, args=[str(FIXTURE)], cwd=str(ROOT)
                    ),
                    {},
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]
                        document = deepcopy(doc)
                        document["policy"]["limits"]["max_operation_calls"] = budget
                        snapshot = assets(document)
                        compiled = compile_workflow(
                            "mcp:group",
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
                                "args": {
                                    "artifact_root": str(root / "output"),
                                    "json": True,
                                }
                            },
                            remote,
                            authorize,
                        )
                        if mode in ["error", "unproved"] or budget < 4:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            expected = 2 if mode == "error" else 3
                            if budget < 4:
                                expected = 2
                                self.assertFalse((root / "calls.jsonl").exists())
                            self.assertEqual(len(result["calls"]), expected)
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            return
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(len(result["calls"]), 4)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        report = result["outputs"]["report"]
                        self.assertEqual(
                            result["outputs"]["exit_code"],
                            0 if mode == "success" else 3,
                        )
                        self.assertEqual(report["ok"], mode == "success")
                        persisted = json.loads(
                            (root / "output/discovery_report.json").read_text()
                        )
                        self.assertNotIn("test_assertions", persisted)
                        self.assertEqual(persisted["candidate_count"], 1)
                        self.assertEqual(persisted["attempt_count"], 1)
                        attempt = report["attempts"][0]
                        selection = attempt["premise_selection_report"]["selected_ids"]
                        self.assertEqual(len(selection), 5)
                        generation = attempt["premise_generation_report"]
                        self.assertEqual(generation["generated_count"], 4)
                        self.assertEqual(generation["attempted_count"], 3)
                        self.assertEqual(
                            len(generation["promoted_ids"]),
                            3 if mode == "success" else 2,
                        )
                        unsafe = generation["generated_lemmas"][-1]
                        self.assertEqual(unsafe["proof_status"], "rejected")
                        self.assertFalse(unsafe["promoted"])
                        trials = attempt["premise_minimization_attempts"]
                        self.assertEqual(
                            len(trials), 5 + len(generation["promoted_ids"])
                        )
                        self.assertEqual(
                            [t["removed_premise_id"] for t in trials[:5]],
                            [
                                "mul_associative",
                                "left_identity",
                                "right_identity",
                                "left_inverse",
                                "right_inverse",
                            ],
                        )
                        self.assertTrue(
                            all(t["ok_without_premise"] for t in trials[:5])
                        )
                        self.assertTrue(all(t["kept"] for t in trials[5:]))
                        calls = [
                            json.loads(line)
                            for line in (root / "calls.jsonl").read_text().splitlines()
                        ]
                        self.assertEqual(len(calls), 3 + len(trials) + 1)
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
                        actual = clean(report)
                        history = (root / "calls.jsonl").read_text()
                        shutil.rmtree(root / "output")
                        (root / "calls.jsonl").unlink()
                        out = io.StringIO()
                        with (
                            patch.dict(os.environ, {"VAMPIRE_BIN": "fixture-vampire"}),
                            patch.object(v.subprocess, "run", side_effect=compiler),
                            patch.object(
                                sys,
                                "argv",
                                [
                                    "group",
                                    "--artifact-root",
                                    str(root / "output"),
                                    "--json",
                                ],
                            ),
                            contextlib.redirect_stdout(out),
                        ):
                            code = oracle()()
                        self.assertEqual(code, result["outputs"]["exit_code"])
                        self.assertEqual(actual, clean(json.loads(out.getvalue())))
                        self.assertEqual(
                            clean(history), clean((root / "calls.jsonl").read_text())
                        )
                    except BaseException as error:
                        import traceback

                        traceback.print_exc()
                        failure = error
                    else:
                        failure = None
                if failure:
                    raise failure
                self.assertFalse(manager.active)

        for mode in ["success", "lemma_fail", "unproved", "error"]:
            asyncio.run(scenario(mode))
        asyncio.run(scenario("success", budget=1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
