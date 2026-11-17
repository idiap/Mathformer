#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source parity, registered MCP interfaces and Lunar/PRISM runtime."""

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
from dataclasses import asdict
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import tempfile
import unittest
import yaml
from agentc_workflow_tools import agentc_module
from agentc_profile_workflow_tools import ProfileSteps, native_options
from agentc_profile_boundary import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"]).resolve()
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/profile/profile_source_grounded_autoformalization_workflow/workflow.yaml"


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
        "profile_original",
        str(ROOT / "tests/mcp/fixtures/agentc_profile_original.py.txt"),
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


def tree(root):
    base = Path(root) / ".lake/packages/mathlib/Mathlib/Algebra"
    base.mkdir(parents=True, exist_ok=True)
    (base / "Group.lean").write_text(
        "namespace Nat\ntheorem add_comm (a b : Nat) : a + b = b + a := by omega\ntheorem add_zero (a : Nat) : a + 0 = a := by omega\nend Nat\n"
    )


def request(directory, case="single"):
    result = {
        "informal_statement": "  Addition is commutative and zero is an identity.  ",
        "agent_configuration": {
            "aspect_description": "Preserve source meaning",
            "max_iterations": 4,
            "default_first_formalization_cycles": 2,
            "default_max_score_gated_cycles": 20,
            "default_target_compatibility_score": 100,
            "latex_expander": True,
            "latex_expansion_completeness_reviewer": True,
            "latex_expansion_binding_reviewer": True,
        },
        "options": {
            "mathlib_concept_loop_max_rounds": 3,
            "mathlib_concept_loop_target_verified_ratio": 1.0,
            "enable_default_multi_cycle": False,
            "enable_concept_mapping": False,
            "enforce_mathlib_alignment": False,
            "enable_llm_judges": False,
            "enable_compatibility_audit": False,
            "enable_lean_consistency_report": False,
            "file_prefix": "fixture",
            "informal_formal_pairs": [["example", "example code"]],
            "concept_map_lean_workdir": str(directory),
            "compatibility_audit_lake_workdir": str(directory),
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
    options = result["options"]
    if case in {"two", "twenty", "early", "consistent", "inconsistent"}:
        options["enable_default_multi_cycle"] = True
    if case in {"twenty", "early", "consistent", "inconsistent"}:
        options["enable_compatibility_audit"] = True
        options["compatibility_target_score"] = 100
    if case in {"consistent", "inconsistent"}:
        options["enable_lean_consistency_report"] = True
    if case == "zero_iterations":
        result["agent_configuration"]["max_iterations"] = 0
    if case == "seed":
        options["seed_formalization"] = ""
    if case == "disabled":
        options["enable_latex_expansion"] = False
    if case == "dependencies":
        options["dependency_statements"] = [
            "Dependency proposition.",
            "  Dependency proposition. ",
        ]
    if case == "cycle":
        options["dependency_statements"] = [result["informal_statement"]]
    if case == "invalid":
        result["informal_statement"] = " "
    if case == "no_refiners":
        result["agent_configuration"]["refinement"] = False
    if case in {"concepts", "concept_once", "concept_init_error"}:
        options["enable_concept_mapping"] = True
        options["enable_latex_expansion"] = False
    if case == "concept_once":
        options["enable_mathlib_concept_compatibility_loop"] = False
    if case == "concept_init_error":
        options["concept_map_top_k"] = 0
    if case == "judges":
        options["enable_llm_judges"] = True
    if case == "context":
        result["native_context"] = {
            "dependency_stack": [],
            "dependency_cache": {},
            "shared_reasoning_log_file": str(Path(directory) / "reasoning.jsonl"),
        }
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


def rows(directory, name):
    p = Path(directory) / name
    return (
        [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []
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

        return re.sub(
            r"agentc_steps/step-[^/\s]+",
            "<compiler>",
            item.replace(str(directory), "<root>"),
        )
    return item


class ProfileTests(unittest.TestCase):
    def test_contract_bindings_and_provenance(self):
        self.assertEqual(
            DOCUMENT,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/agentc-profile.workflow.json"
                ).read_text()
            ),
        )
        self.assertEqual(
            DOCUMENT["id"], "profile_source_grounded_autoformalization_workflow"
        )
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        for source in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "skills/autoformalization/autoformalization-agentc/scripts/agentc.py",
            [s["path"] for s in DOCUMENT["provenance"]["sources"]],
        )

    def test_state_and_stale_capability_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp, cwd(tmp):
            factory, calls = install(agentc_module(), tmp, "semantic")
            engine = ProfileSteps(DOCUMENT, factory)
            state = engine.call(
                "normalize_and_pack_cycles", {"request": request(tmp, "dependencies")}
            )["state"]
            work = engine.call("dependencies_expand_annotate", {"state": state})["work"]
            self.assertEqual(len(work["dependency_cache"]), 1)
            self.assertEqual(len(work["dependency_reports"]), 2)
            self.assertEqual(len(work["effective_pairs"]), 3)
            self.assertTrue(work["dependency_stack"])
            stack = next(iter(engine.sessions.values()))["native"]["dependency_stack"]
            with self.assertRaisesRegex(ValueError, "stale or modified"):
                engine.call("initialize_concepts", {"work": {**work, "revision": 999}})
            self.assertFalse(stack)
            self.assertFalse(engine.sessions)

    def test_lunar_parser_checker_compiler_runtime_and_original_parity(self):
        asyncio.run(self.run_cases())

    async def run_cases(self):
        cases = [
            ("single", "ok"),
            ("disabled", "ok"),
            ("seed", "ok"),
            ("single", "expand_failure"),
            ("single", "review_false"),
            ("two", "ok"),
            ("early", "consistent"),
            ("consistent", "consistent"),
            ("inconsistent", "consistent"),
            ("twenty", "ok"),
            ("dependencies", "ok"),
            ("context", "ok"),
            ("single", "refine"),
            ("single", "semantic"),
            ("single", "refinement_cap"),
            ("no_refiners", "refine"),
            ("zero_iterations", "refine"),
            ("judges", "ok"),
            ("concepts", "ok"),
            ("concepts", "concept_widen"),
            ("concepts", "concept_cap"),
            ("concepts", "concept_error"),
            ("concepts", "concept_later_error"),
            ("concept_once", "ok"),
            ("concept_init_error", "ok"),
            ("single", "draft_failure"),
            ("single", "compiler_failure"),
            ("cycle", "ok"),
            ("invalid", "ok"),
        ]
        seen = set()
        for case, mode in cases:
            with (
                self.subTest(case=case, mode=mode),
                tempfile.TemporaryDirectory() as tmp,
            ):
                original_dir = Path(tmp) / "oracle"
                remote_dir = Path(tmp) / "remote"
                original_dir.mkdir()
                remote_dir.mkdir()
                tree(original_dir)
                tree(remote_dir)
                original = oracle()
                factory, native_calls = install(original, original_dir, mode)
                req = request(original_dir, case)
                # Inconsistent stop is exercised with a compatibility-success candidate
                # whose actual consistency threshold is intentionally unattainable.
                if case == "inconsistent":
                    req["options"]["lean_consistency_target_reference_free_score"] = 101
                expected = error = None
                with cwd(original_dir):
                    try:
                        with factory(req) as agent:
                            expected = asdict(
                                agent.run_systematic_workflow(
                                    req["informal_statement"], **native_options(req)
                                )
                            )
                    except (ValueError, TimeoutError, OSError) as exc:
                        error = exc
                remote_request = request(remote_dir, case)
                if case == "inconsistent":
                    remote_request["options"][
                        "lean_consistency_target_reference_free_score"
                    ] = 101
                manager = SessionManager()
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
                code = "from agentc_profile_boundary import serve; import sys; serve(sys.argv[1],sys.argv[2])"
                failure = None
                async with manager.open(
                    "profile-fixture",
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
                        snapshot = assets(DOCUMENT)
                        workflow = workflow_documents([DESCRIPTOR], snapshot)[0]
                        compiled = compile_workflow(
                            "mcp:profile-fixture", workflow, tools
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(DOCUMENT["operations"])
                        )

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
                        else:
                            self.assertEqual(
                                result["status"],
                                "accepted",
                                {
                                    k: result.get(k)
                                    for k in ("status", "calls", "failure_disposition")
                                },
                            )
                            report = result["outputs"]["report"]
                            seen.update(c["operation"] for c in result["calls"])
                            self.assertEqual(
                                result["outputs"]["code"], expected["final_code"]
                            )
                            self.assertEqual(
                                result["outputs"]["output_file"], report["output_file"]
                            )
                            for key in (
                                "final_code",
                                "normalized_statement",
                                "effective_statement",
                                "expanded_statement",
                                "latex_expansion_review_passed",
                                "initial_correctness",
                                "final_correctness",
                                "final_saved_file_correctness",
                                "used_iterative_refinement",
                                "compatibility_target_met",
                                "consistency_target_met",
                                "cycle_index",
                                "cycle_count",
                                "concept_map_error",
                            ):
                                self.assertEqual(
                                    report.get(key), expected.get(key), key
                                )
                            self.assertEqual(
                                stable(
                                    json.loads(
                                        Path(report["history_file"]).read_text()
                                    ),
                                    remote_dir,
                                ),
                                stable(
                                    json.loads(
                                        Path(expected["history_file"]).read_text()
                                    ),
                                    original_dir,
                                ),
                            )
                            self.assertEqual(
                                stable(report["mathlib_concept_coverage"], remote_dir),
                                stable(
                                    expected["mathlib_concept_coverage"], original_dir
                                ),
                            )
                            self.assertEqual(
                                Path(report["output_file"]).read_text(),
                                Path(expected["output_file"]).read_text(),
                            )
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            cycles = sum(
                                c["operation"] == "advance_cycles_and_guards"
                                for c in result["calls"]
                            )
                            self.assertEqual(
                                cycles,
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
                                self.assertEqual(len(manifest["cycles"]), cycles)
                                self.assertTrue(
                                    all(
                                        c["seeded_from_previous_cycle"]
                                        for c in manifest["cycles"][1:]
                                    )
                                )
                            history = json.loads(
                                Path(report["history_file"]).read_text()
                            )
                            if mode == "refinement_cap":
                                self.assertEqual(history[-1]["round_index"], 4)
                                self.assertEqual(report["final_correctness"], "False")
                            if mode == "semantic":
                                self.assertEqual(
                                    [h["agent_name"] for h in history],
                                    [
                                        "AutoformalizationAgent",
                                        "FormalRefinementAgent",
                                        "InformalRefinementAgent",
                                        "EarlyStop",
                                    ],
                                )
                            if case.startswith("concept"):
                                rounds = (
                                    report["mathlib_concept_compatibility_rounds"] or []
                                )
                                self.assertEqual(
                                    len(rounds),
                                    (
                                        3
                                        if mode
                                        in {"concept_cap", "concept_later_error"}
                                        else (
                                            2
                                            if mode == "concept_widen"
                                            else (
                                                0 if case == "concept_init_error" else 1
                                            )
                                        )
                                    ),
                                )
                                if len(rounds) > 1:
                                    self.assertEqual(
                                        [r["top_k"] for r in rounds],
                                        [8, 12, 16][: len(rounds)],
                                    )
                        self.assertEqual(
                            [r["kind"] for r in rows(remote_dir, "calls.jsonl")],
                            [r["kind"] for r in native_calls],
                        )
                        self.assertEqual(
                            [r["step"] for r in rows(remote_dir, "reasoning.jsonl")],
                            [r["step"] for r in rows(original_dir, "reasoning.jsonl")],
                        )
                    except Exception as exc:
                        failure = exc
                if failure is not None:
                    raise failure
                self.assertFalse(manager.active)
        self.assertEqual(seen, set(DOCUMENT["operations"]))


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
