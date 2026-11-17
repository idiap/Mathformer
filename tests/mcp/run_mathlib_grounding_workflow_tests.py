#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - the test launcher selects Lunar before third-party imports
"""Real source, mapper, MCP and Lunar/PRISM execution without live compilers."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from agentc_workflow_tools import agentc_module
from mathlib_grounding_workflow_tools import GroundingSteps
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"]).resolve()
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_mathlib_grounding_loop_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/mathlib-grounding.workflow.json"
)
FIXTURES = ROOT / "tests/mcp/fixtures"
PYTHONPATH = os.pathsep.join(
    [
        str(FIXTURES / "mathlib_compiler"),
        str(FIXTURES),
        str(ROOT / "scripts"),
        *[str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")],
    ]
)


def snapshot(document):
    values = {
        s["path"]: (ROOT / s["path"]).read_text()
        for s in document["provenance"]["sources"]
    }
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


def tree(root):
    mathlib = root / ".lake/packages/mathlib/Mathlib"
    mathlib.mkdir(parents=True)
    # Enough genuine declaration headers for widening candidates and modules.
    for module in ["Algebra/Group", "Algebra/Ring", "Algebra/Monoid", "Algebra/Field"]:
        file = (mathlib / module).with_suffix(".lean")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            "\n".join(
                f"theorem {name}_{module.split('/')[-1]} : True := by trivial"
                for name in ["add_comm", "mul_comm", "identity", "one_mul", "mul_one"]
            )
        )


def read_jsonl(path):
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def stable(value, root):
    if isinstance(value, dict):
        return {k: stable(v, root) for k, v in value.items() if k != "duration_ms"}
    if isinstance(value, (list, tuple)):
        return [stable(v, root) for v in value]
    if isinstance(value, str):
        return value.replace(str(root), "<workdir>")
    return value


def original():
    namespace = dict(vars(agentc_module()))
    exec(
        compile(
            (FIXTURES / "mathlib_grounding_original.py.txt").read_text(),
            str(FIXTURES / "mathlib_grounding_original.py.txt"),
            "exec",
        ),
        namespace,
    )
    return namespace["run_mathlib_concept_compatibility_loop"]


class GroundingTests(unittest.TestCase):
    def test_authored_contract_provenance_and_source_projection(self):
        self.assertEqual(DOCUMENT, json.loads(AUTHORED.read_text()))
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertIn(
            "skills/autoformalization/autoformalization-agentc/scripts/agentc.py",
            [s["path"] for s in DOCUMENT["provenance"]["sources"]],
        )
        for source in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            all(
                o["execution"]["binding"]["target"]
                == o["execution"]["binding"]["operation"]
                for o in DOCUMENT["operations"].values()
            )
        )

    def test_state_defaults_guards_widening_and_native_callback_scope(self):
        service = GroundingSteps(DOCUMENT, lambda: None, lambda path: True)
        state = service.call(
            "initialize", {"request": {"statement": "commutative"}, "context": {}}
        )["state"]
        self.assertEqual(
            [
                state[k]
                for k in [
                    "current_top_k",
                    "current_top_modules",
                    "current_verify_max_concepts",
                    "current_verify_max_candidates",
                ]
            ],
            [8, 12, 6, 3],
        )
        request = dict(
            statement="commutative",
            top_k=3,
            top_modules=5,
            verify_max_concepts=1,
            verify_max_candidates=1,
        )
        advanced = service.call(
            "pack_transition", dict(request=request, state=state, widen=True)
        )["state"]
        self.assertEqual(
            [
                advanced[k]
                for k in [
                    "current_top_k",
                    "current_top_modules",
                    "current_verify_max_concepts",
                    "current_verify_max_candidates",
                    "round_index",
                ]
            ],
            [10, 14, 8, 4, 2],
        )
        for best, failed, ratio, target, index, early, done in [
            (None, True, None, 1, 1, True, True),
            ({}, True, None, 1, 1, False, False),
            ({}, False, None, 0, 1, False, False),
            ({}, False, 0.5, 0.5, 1, True, True),
            ({}, False, 0, 1, 3, False, True),
        ]:
            args = dict(
                state={
                    **state,
                    "best_map": best,
                    "target_verified_ratio": target,
                    "round_index": index,
                },
                status={
                    "failed": failed,
                    "verified_ratio": ratio,
                    "target_met": not failed
                    and isinstance(ratio, (int, float))
                    and ratio >= target,
                },
            )
            self.assertEqual(
                service.call("compute_guards", args), dict(early_stop=early, done=done)
            )
        for target, expected in [(-1, 0), (2, 1)]:
            initial = service.call(
                "initialize",
                dict(
                    request=dict(statement="s", target_verified_ratio=target),
                    context={},
                ),
            )["state"]
            self.assertEqual(initial["target_verified_ratio"], expected)
        for request in [
            dict(statement="s", max_rounds=2),
            dict(statement="s", top_k=0),
        ]:
            with self.assertRaisesRegex(ValueError, "schema"):
                service.call("initialize", dict(request=request, context={}))

        def denied():
            raise PermissionError("readonly fixture")

        with self.assertRaisesRegex(PermissionError, "readonly fixture"):
            GroundingSteps(DOCUMENT, denied, lambda p: True).call(
                "initialize", dict(request={"statement": "s"}, context={})
            )
        with self.assertRaisesRegex(ValueError, "write roots"):
            GroundingSteps(DOCUMENT, lambda: None, lambda p: False).call(
                "initialize", dict(request={"statement": "s"}, context={})
            )
        # Native validation and callback exceptions before the try are unchanged.
        for function in [
            original(),
            agentc_module().run_mathlib_concept_compatibility_loop,
        ]:
            with self.assertRaisesRegex(ValueError, "max_rounds"):
                function("x", max_rounds=0)

            def reject(event, payload):
                raise OSError("callback failure")

            with self.assertRaisesRegex(OSError, "callback failure"):
                function("x", trace_event=reject)

    def test_registered_mcp_lunar_prism_runtime_and_original_parity(self):
        asyncio.run(self.cases())

    async def cases(self):
        for mode in [
            "success",
            "widen",
            "fail",
            "partial",
            "later_error",
            "first_error",
            "timeout",
            "missing_compiler",
            "empty",
            "no_verify",
            "zero_target",
        ]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                native_root, remote_root, shared_root = [
                    base / name for name in ["native", "remote", "shared"]
                ]
                for directory in [native_root, remote_root, shared_root]:
                    tree(directory)
                env = {
                    "PYTHONPATH": PYTHONPATH,
                    "MATHLIB_COMPILER_CASE": mode,
                    "PYTHONDONTWRITEBYTECODE": "1",
                }

                def request(root):
                    result = dict(
                        statement="commutative identity",
                        lean_workdir=str(root),
                        verify_timeout_sec=17,
                        reasoning_log_file=str(root / "mapping.jsonl"),
                        top_k=3,
                        top_modules=5,
                        verify_max_concepts=1,
                        verify_max_candidates=1,
                    )
                    if mode == "success":
                        result["statement"] = "commutative"
                    if mode == "empty":
                        result.update(statement="the and", target_verified_ratio=0)
                    if mode == "no_verify":
                        result["verify_checks"] = False
                    if mode == "zero_target":
                        result["target_verified_ratio"] = -2
                    return result

                events = []
                with patch.dict(os.environ, env):
                    expected = original()(
                        **request(native_root),
                        trace_event=lambda event, payload: events.append(
                            dict(event=event, payload=deepcopy(payload))
                        ),
                    )
                    shared_events = []
                    shared = agentc_module().run_mathlib_concept_compatibility_loop(
                        **request(shared_root),
                        trace_event=lambda e, p: shared_events.append(
                            dict(event=e, payload=deepcopy(p))
                        ),
                    )
                self.assertEqual(
                    stable(shared, shared_root), stable(expected, native_root)
                )
                self.assertEqual(
                    stable(shared_events, shared_root), stable(events, native_root)
                )
                manager = SessionManager()
                code = "from mathlib_grounding_boundary import serve; import sys; serve(sys.argv[1])"
                async with manager.open(
                    "grounding-fixture",
                    StdioConfig(
                        command=sys.executable,
                        args=["-c", code, str(remote_root)],
                        cwd=str(ROOT),
                    ),
                    env,
                ) as remote:
                    failure = None
                    try:
                        tools = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compile_document(document):
                            assets = snapshot(document)
                            workflow = workflow_documents([DESCRIPTOR], assets)[0]
                            self.assertTrue(workflow["validation"]["valid"], workflow)
                            compiled = compile_workflow(
                                "mcp:grounding-fixture", workflow, tools
                            )
                            self.assertTrue(
                                compiled["runnable"], compiled["diagnostics"]
                            )
                            self.assertEqual(
                                set(compiled["bindings"]), set(document["operations"])
                            )
                            return compiled, assets

                        compiled, assets = compile_document(DOCUMENT)

                        async def authorize():
                            pass

                        context = dict(
                            trace_log_file=str(remote_root / "trace.jsonl"),
                            file_prefix="fixture",
                            dependency_label="native-context",
                        )
                        result = await execute(
                            compiled,
                            assets,
                            dict(request=request(remote_root), context=context),
                            remote,
                            authorize,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        output = result["outputs"]
                        self.assertEqual(
                            stable(
                                [
                                    output[k]
                                    for k in [
                                        "best_map",
                                        "coverage",
                                        "rounds",
                                        "last_error",
                                    ]
                                ],
                                remote_root,
                            ),
                            stable(expected, native_root),
                        )
                        trace = read_jsonl(remote_root / "trace.jsonl")
                        self.assertEqual(
                            [e["step"] for e in trace], [e["event"] for e in events]
                        )
                        for actual, expected_event in zip(trace, events):
                            payload = {
                                k: actual["payload"][k]
                                for k in expected_event["payload"]
                            }
                            self.assertEqual(
                                stable(payload, remote_root),
                                stable(expected_event["payload"], native_root),
                            )
                            self.assertEqual(actual["file_prefix"], "fixture")
                            self.assertEqual(
                                actual["dependency_label"], "native-context"
                            )
                        rounds = output["rounds"]
                        expected_count = {
                            "success": 1,
                            "widen": 2,
                            "first_error": 1,
                            "zero_target": 1,
                        }.get(mode, 3)
                        self.assertEqual(len(rounds), expected_count)
                        self.assertEqual(len(result["calls"]), 2 + 3 * expected_count)
                        self.assertEqual(
                            [r["top_k"] for r in rounds],
                            [3 + 2 * i for i in range(expected_count)],
                        )
                        self.assertEqual(
                            [r["top_modules"] for r in rounds],
                            [5 + 2 * i for i in range(expected_count)],
                        )
                        self.assertEqual(
                            [r["verify_max_concepts"] for r in rounds],
                            [1 + 2 * i for i in range(expected_count)],
                        )
                        self.assertEqual(
                            [r["verify_max_candidates"] for r in rounds],
                            [1 + i for i in range(expected_count)],
                        )
                        compiler = read_jsonl(remote_root / "compiler.jsonl")
                        if mode in ["empty", "no_verify"]:
                            self.assertEqual(compiler, [])
                        else:
                            self.assertEqual(len(compiler), expected_count)
                            self.assertTrue(
                                all("#check" in c["content"] for c in compiler)
                            )
                        mapping_events = read_jsonl(remote_root / "mapping.jsonl")
                        self.assertTrue(mapping_events)
                        self.assertEqual(
                            len(
                                [
                                    e
                                    for e in mapping_events
                                    if e["step"] == "concept_mapping_cli_start"
                                ]
                            ),
                            expected_count,
                        )
                        if mode == "empty":
                            self.assertEqual(output["best_map"], {})
                            self.assertIsNone(output["coverage"]["verified_ratio"])
                        if mode == "first_error":
                            self.assertIsNone(output["best_map"])
                            self.assertIn(
                                "fixture compiler launch error", output["last_error"]
                            )
                        if mode == "later_error":
                            self.assertIn(
                                "fixture compiler launch error", output["last_error"]
                            )
                            self.assertIsNone(rounds[1]["coverage"])
                            self.assertIsNone(rounds[-1]["error"])
                        if mode in ["fail", "partial", "timeout", "missing_compiler"]:
                            # Equal score replaces the map, including round-specific
                            # errors; lower score retains the prior best coverage.
                            errors = [
                                err
                                for p in output["best_map"].values()
                                for c in p["candidates"]
                                for err in c.get("check_errors", [])
                            ]
                            self.assertTrue(errors)
                            if mode in ["fail", "partial"]:
                                self.assertTrue(
                                    any("round 3" in e for e in errors), errors
                                )
                        if mode == "partial":
                            scores = [r["coverage"]["coverage_score"] for r in rounds]
                            self.assertGreater(scores[0], scores[1])
                            self.assertEqual(scores[0], scores[2])
                        if mode == "fail":
                            log_failure = await execute(
                                compiled,
                                assets,
                                dict(
                                    request=request(remote_root),
                                    context={"trace_log_file": str(remote_root)},
                                ),
                                remote,
                                authorize,
                            )
                            self.assertEqual(
                                log_failure["status"], "failed", log_failure
                            )
                            self.assertIsNone(log_failure["outputs"])
                            self.assertEqual(len(log_failure["calls"]), 1)
                            # Native cap returns normally; a truncated structural
                            # bound must fail with no terminal output.
                            bounded = deepcopy(DOCUMENT)
                            bounded["flow"]["steps"][1]["max_iterations"] = 1
                            cut, cut_assets = compile_document(bounded)
                            exhausted = await execute(
                                cut,
                                cut_assets,
                                dict(request=request(remote_root), context={}),
                                remote,
                                authorize,
                            )
                            self.assertEqual(exhausted["status"], "failed", exhausted)
                            self.assertIsNone(exhausted["outputs"])
                            self.assertFalse(
                                any(
                                    c["operation"] == "finish"
                                    for c in exhausted["calls"]
                                )
                            )
                            # Logging errors outside the native try propagate to the
                            # workflow and never fabricate a successful completion.
                            bad_request = {
                                **request(remote_root),
                                "lean_workdir": str(base / "outside"),
                            }
                            rejected = await execute(
                                compiled,
                                assets,
                                dict(request=bad_request, context={}),
                                remote,
                                authorize,
                            )
                            self.assertEqual(rejected["status"], "failed", rejected)
                            self.assertIsNone(rejected["outputs"])
                            self.assertEqual(len(rejected["calls"]), 1)
                    except Exception as error:
                        failure = error
                self.assertFalse(manager.active)
                if failure is not None:
                    raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
