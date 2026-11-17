#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native readiness parity and real MCP/Lunar PRISM execution, entirely offline."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml
from agentc_workflow_tools import agentc_module
from agentc_readiness_workflow_tools import ReadinessSteps
from agentc_readiness_boundary import install, CODE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"]).resolve()
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_preformalization_readiness_loop_workflow/workflow.yaml"


@contextmanager
def cwd(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def oracle():
    loader = SourceFileLoader(
        "readiness_original",
        str(ROOT / "tests/mcp/fixtures/agentc_readiness_original.py.txt"),
    )
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    sys.modules[loader.name] = module
    module.__file__ = str(
        ROOT / "skills/autoformalization/autoformalization-agentc/scripts/agentc.py"
    )
    exec(
        compile(Path(loader.path).read_text(), module.__file__, "exec"), module.__dict__
    )
    return module


def request(directory, case="single"):
    result = {
        "informal_statement": "  A true proposition.  ",
        "constructor_defaults": {
            "default_first_formalization_cycles": 2,
            "default_max_score_gated_cycles": 20,
        },
        "agent_context": {
            "aspect_description": "Preserve source meaning",
            "max_iterations": 2,
            "latex_expander": True,
            "latex_expansion_completeness_reviewer": True,
            "latex_expansion_binding_reviewer": True,
        },
        "options": {
            "enable_default_multi_cycle": False,
            "enable_concept_mapping": False,
            "enforce_mathlib_alignment": False,
            "enable_llm_judges": False,
            "enable_compatibility_audit": False,
            "enable_lean_consistency_report": False,
            "file_prefix": "fixture",
            "informal_formal_pairs": [["example", "example code"]],
            **{
                key: str(Path(directory) / name)
                for key, name in [
                    ("output_file", "result.lean"),
                    ("report_file", "report.json"),
                    ("history_file", "history.json"),
                    ("reasoning_log_file", "reasoning.jsonl"),
                ]
            },
        },
    }
    if case in {"two", "twenty", "early", "consistent", "inconsistent"}:
        result["options"]["enable_default_multi_cycle"] = True
    if case in {"twenty", "early", "consistent", "inconsistent"}:
        result["options"]["enable_compatibility_audit"] = True
        result["options"]["compatibility_target_score"] = 101 if case == "twenty" else 0
        # The actual audit executes in-process with the compiler fixture.
    if case in {"consistent", "inconsistent"}:
        result["options"]["enable_lean_consistency_report"] = True
    if case == "zero_iterations":
        result["agent_context"]["max_iterations"] = 0
    if case == "seed":
        result["options"]["seed_formalization"] = ""
    if case == "disabled":
        result["options"]["enable_latex_expansion"] = False
    if case == "unconfigured":
        result["agent_context"]["latex_expander"] = False
    if case == "missing_reviewers":
        result["agent_context"]["latex_expansion_completeness_reviewer"] = False
        result["agent_context"]["latex_expansion_binding_reviewer"] = False
    if case == "dependencies":
        result["options"]["dependency_statements"] = [
            "Dependency proposition.",
            "  Dependency proposition. ",
        ]
    if case == "cycle":
        result["options"]["dependency_statements"] = [result["informal_statement"]]
    if case == "invalid":
        result["informal_statement"] = "   "
    if case == "no_refiners":
        result["agent_context"]["refinement"] = False
    return result


def assets(document):
    values = {
        s["path"]: (ROOT / s["path"]).read_text()
        for s in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in values.items()
    ]


def read_rows(directory, name):
    path = Path(directory) / name
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def stable(item, directory):
    if isinstance(item, dict):
        return {
            k: stable(v, directory)
            for k, v in item.items()
            if k
            not in {
                "step_timings_ms",
                "duration_ms",
                "error_log_path",
                "error_log_text",
                "timestamp",
                "timestamp_utc",
                "timestamp_ms",
                "elapsed_ms_since_prev_event",
                "elapsed_ms_since_start",
            }
        }
    if isinstance(item, list):
        return [stable(v, directory) for v in item]
    if isinstance(item, str):
        import re

        item = item.replace(str(directory), "<root>")
        item = re.sub(r"agentc_steps/step-[^/\s]+", "<compiler>", item)
        return item
    return item


class ReadinessTests(unittest.TestCase):
    def test_contract_identity_bindings_and_source_digests(self):
        self.assertEqual(
            DOCUMENT,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/agentc-readiness.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(
            DOCUMENT["id"], "loop_preformalization_readiness_loop_workflow"
        )
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertIn(
            "skills/autoformalization/autoformalization-agentc/scripts/agentc.py",
            [s["path"] for s in DOCUMENT["provenance"]["sources"]],
        )
        for row in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

    def test_native_state_ports_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp, cwd(tmp):
            factory, calls = install(agentc_module(), tmp, "review_false")
            engine = ReadinessSteps(DOCUMENT, factory)
            req = request(tmp, "dependencies")
            state = engine.call("initialize", {"request": req})["state"]
            dep = engine.call("dependencies", {"state": state})
            self.assertTrue(dep["expand"])
            self.assertEqual(len(dep["invocation"]["dependency_reports"]), 2)
            self.assertEqual(len(dep["invocation"]["state"]["dependency_cache"]), 1)
            expanded = engine.call("expand", {"invocation": dep["invocation"]})[
                "invocation"
            ]
            review = engine.call("review", {"invocation": expanded})["invocation"]
            self.assertFalse(review["review_passed"])
            self.assertEqual(
                [r["name"] for r in review["reviews"]], ["completeness", "bindings"]
            )
            prepared = engine.call("prepare", {"invocation": review})["invocation"]
            self.assertEqual(
                prepared["effective_pairs"][-1], ["example", "example code"]
            )
            self.assertEqual(len(prepared["effective_pairs"]), 3)
            self.assertIn("Dependency proposition", prepared["dependency_context"])
            drafted = engine.call("draft", {"invocation": prepared})["invocation"]
            self.assertEqual(drafted["initial_code"].strip(), CODE)
            checked = engine.call("check_report_save", {"invocation": drafted})
            advanced = engine.call("advance", checked)
            self.assertTrue(advanced["stop"])
            self.assertEqual(advanced["state"]["dependency_stack"], [])
            self.assertEqual(len(advanced["state"]["dependency_cache"]), 1)
            finished = engine.call("finish", {"state": advanced["state"]})
            self.assertEqual(finished["report"]["final_code"].strip(), CODE)
            self.assertFalse(engine.sessions)
            self.assertIn(
                "dependency_cache_hit",
                [r["step"] for r in read_rows(tmp, "reasoning.jsonl")],
            )
            state = engine.call("initialize", {"request": request(tmp)})["state"]
            dep = engine.call("dependencies", {"state": state})
            native_stack = next(iter(engine.sessions.values()))[
                "iterator"
            ].gi_frame.f_locals["dependency_stack"]
            self.assertTrue(native_stack)
            with self.assertRaisesRegex(ValueError, "stale or modified"):
                engine.call(
                    "expand", {"invocation": {**dep["invocation"], "revision": 99}}
                )
            self.assertFalse(native_stack)
            self.assertFalse(engine.sessions)

    def test_lunar_native_parser_checker_compiler_runtime_and_parity(self):
        asyncio.run(self.run_cases())

    async def run_cases(self):
        cases = [
            ("single", "ok"),
            ("disabled", "ok"),
            ("unconfigured", "ok"),
            ("seed", "ok"),
            ("single", "empty"),
            ("single", "expand_failure"),
            ("single", "review_false"),
            ("single", "completeness_failure"),
            ("missing_reviewers", "ok"),
            ("two", "ok"),
            ("early", "review_false"),
            ("consistent", "consistent"),
            ("inconsistent", "ok"),
            ("twenty", "ok"),
            ("dependencies", "ok"),
            ("single", "refine"),
            ("single", "refinement_cap"),
            ("no_refiners", "refine"),
            ("zero_iterations", "refine"),
            ("single", "draft_failure"),
            ("single", "compiler_failure"),
            ("cycle", "ok"),
            ("invalid", "ok"),
        ]
        for case, mode in cases:
            with (
                self.subTest(case=case, mode=mode),
                tempfile.TemporaryDirectory() as tmp,
            ):
                original_dir = Path(tmp) / "oracle"
                remote_dir = Path(tmp) / "remote"
                original_dir.mkdir()
                remote_dir.mkdir()
                original = oracle()
                factory, native_calls = install(original, original_dir, mode)
                req = request(original_dir, case)
                expected = None
                error = None
                with cwd(original_dir):
                    try:
                        with factory(req) as agent:
                            expected = asdict(
                                agent.run_systematic_workflow(
                                    req["informal_statement"], **req["options"]
                                )
                            )
                    except (ValueError, TimeoutError, OSError) as exc:
                        error = exc
                manager = SessionManager()
                remote_request = request(remote_dir, case)
                env = {
                    "PYTHONPATH": os.pathsep.join(
                        [
                            str(ROOT / "tests/mcp/fixtures"),
                            str(ROOT / "scripts"),
                            *[
                                str(p)
                                for p in (ROOT / ".venv/lib").glob(
                                    "python*/site-packages"
                                )
                            ],
                        ]
                    )
                }
                code = "from agentc_readiness_boundary import serve; import sys; serve(sys.argv[1],sys.argv[2])"
                failure = None
                async with manager.open(
                    "readiness-fixture",
                    StdioConfig(
                        command=sys.executable,
                        args=["-c", code, str(remote_dir), mode],
                        cwd=str(remote_dir),
                    ),
                    env,
                ) as remote:
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compile_document(document):
                            snapshot = assets(document)
                            workflow = workflow_documents([DESCRIPTOR], snapshot)[0]
                            compiled = compile_workflow(
                                "mcp:readiness-fixture", workflow, tools
                            )
                            self.assertTrue(
                                compiled["runnable"], compiled["diagnostics"]
                            )
                            self.assertEqual(
                                set(compiled["bindings"]), set(document["operations"])
                            )
                            return compiled, snapshot

                        compiled, snapshot = compile_document(DOCUMENT)

                        async def authorize():
                            pass

                        result = await execute(
                            compiled,
                            snapshot,
                            {"request": remote_request},
                            remote,
                            authorize,
                        )
                        if error:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                [
                                    r["kind"]
                                    for r in read_rows(remote_dir, "calls.jsonl")
                                ],
                                [r["kind"] for r in native_calls],
                            )
                            continue
                        self.assertEqual(
                            result["status"],
                            "accepted",
                            {
                                k: result.get(k)
                                for k in ["status", "calls", "failure_disposition"]
                            },
                        )
                        report = result["outputs"]["report"]
                        for key in [
                            "final_code",
                            "normalized_statement",
                            "effective_statement",
                            "expanded_statement",
                            "latex_expansion_review_passed",
                            "initial_correctness",
                            "final_correctness",
                            "used_iterative_refinement",
                            "compatibility_target_met",
                            "consistency_target_met",
                            "cycle_index",
                            "cycle_count",
                        ]:
                            self.assertEqual(report.get(key), expected.get(key), key)
                        self.assertEqual(
                            stable(
                                json.loads(Path(report["history_file"]).read_text()),
                                remote_dir,
                            ),
                            stable(
                                json.loads(Path(expected["history_file"]).read_text()),
                                original_dir,
                            ),
                        )
                        self.assertEqual(
                            [r["kind"] for r in read_rows(remote_dir, "calls.jsonl")],
                            [r["kind"] for r in native_calls],
                        )
                        self.assertEqual(
                            [
                                r["step"]
                                for r in read_rows(remote_dir, "reasoning.jsonl")
                            ],
                            [
                                r["step"]
                                for r in read_rows(original_dir, "reasoning.jsonl")
                            ],
                        )
                        self.assertEqual(
                            Path(report["output_file"]).read_text(),
                            Path(expected["output_file"]).read_text(),
                        )
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            (
                                20
                                if case in {"twenty", "inconsistent"}
                                else 2 if case == "two" else 1
                            ),
                        )
                        if case in {
                            "two",
                            "twenty",
                            "early",
                            "consistent",
                            "inconsistent",
                        }:
                            manifest = json.loads(
                                Path(report["cycle_manifest_file"]).read_text()
                            )
                            self.assertEqual(
                                len(manifest["cycles"]),
                                (
                                    20
                                    if case in {"twenty", "inconsistent"}
                                    else 1 if case in {"early", "consistent"} else 2
                                ),
                            )
                            self.assertTrue(
                                all(
                                    c["seeded_from_previous_cycle"]
                                    for c in manifest["cycles"][1:]
                                )
                            )
                        if case == "early":
                            self.assertTrue(report["compatibility_target_met"])
                            self.assertFalse(report["latex_expansion_review_passed"])
                        if case == "consistent":
                            self.assertTrue(report["compatibility_target_met"])
                            self.assertTrue(report["consistency_target_met"])
                        if case == "inconsistent":
                            self.assertTrue(report["compatibility_target_met"])
                            self.assertFalse(report["consistency_target_met"])
                        if case in {"zero_iterations", "no_refiners"}:
                            self.assertFalse(report["used_iterative_refinement"])
                        if mode == "refinement_cap":
                            self.assertEqual(report["final_correctness"], "False")
                            self.assertEqual(
                                json.loads(Path(report["history_file"]).read_text())[
                                    -1
                                ]["round_index"],
                                2,
                            )
                        if case == "two":
                            limited = deepcopy(DOCUMENT)
                            limited["flow"]["steps"][1]["max_iterations"] = 1
                            short, snap = compile_document(limited)
                            exhausted = await execute(
                                short,
                                snap,
                                {"request": remote_request},
                                remote,
                                authorize,
                            )
                            self.assertEqual(exhausted["status"], "failed")
                            self.assertIsNone(exhausted["outputs"])
                    except Exception as exc:
                        failure = exc
                self.assertFalse(manager.active)
                if failure:
                    raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
