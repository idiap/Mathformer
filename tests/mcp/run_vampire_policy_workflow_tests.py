#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native-source parity and real MCP/Lunar/PRISM execution."""

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
import importlib.util
import io
import json
import re
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch
import yaml
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session
from mcp_connections.client import RemoteSession
from mcp_connections.contracts import workflow_documents
from mcp_connections.execution import execute
from mcp_connections.workflow_compiler import compile_workflow
import vampire_policy_tools as tools
from vampire_policy_boundary import Compiler
from backends.atp.MathformerATP import vampire as v

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_example_vampire_policy_workflow/workflow.yaml"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
POLICY = (ROOT / "examples/vampire_policy_chain_input.md").read_text()
SUBSET = (
    "The subset relation is transitive: every subset of a subset of T is a subset of T."
)
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)


def assets(doc):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {row["path"] for row in doc["provenance"]["sources"]}
    paths.add(
        "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
    )
    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


def clean(value):
    if isinstance(value, dict):
        return {
            k: clean(val)
            for k, val in value.items()
            if k not in ("generated_at", "elapsed_seconds")
        }
    if isinstance(value, list):
        return [clean(val) for val in value]
    return (
        re.sub(r"\d{4}-\d\d-\d\dT[0-9:.]+\+00:00", "<time>", value)
        if isinstance(value, str)
        else value
    )


@contextlib.contextmanager
def environment(root, statement=POLICY, **compiler_args):
    input_path = root / "examples/vampire_policy_chain_input.md"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(statement)
    (root / "examples/vampire_informal_to_proofs.py").write_text(
        "# test repository preflight path\n"
    )
    artifact = root / "artifacts/vampire_atp/policy_chain_example"
    compiler = Compiler(root, **compiler_args)
    # Paths are test invocation inputs; only the external process/resolver are replaced.
    # No credentials or provider environment are read by the native constructor.
    with (
        patch.object(tools.hub, "REPO_ROOT", root),
        patch.object(tools.hub, "REPORT_DIR", root / "artifacts/workflow_hub"),
        patch.object(tools.source(), "INPUT_PATH", input_path),
        patch.object(tools.source(), "ARTIFACT_ROOT", artifact),
        patch.dict(os.environ, {"VAMPIRE_BIN": "fixture-vampire"}),
        patch.object(v.subprocess, "run", side_effect=compiler),
    ):
        try:
            yield compiler, artifact
        finally:
            compiler.ledger.cleanup()


def original_module():
    module = types.ModuleType("policy_original_oracle")
    module.__file__ = str(ROOT / "backends/atp/MathformerATP/vampire.py")
    module.__package__ = "backends.atp.MathformerATP"
    sys.modules[module.__name__] = module
    exec(
        (ROOT / "tests/mcp/fixtures/vampire_policy_original.py.txt").read_text(),
        module.__dict__,
    )
    return module


class PolicyTests(unittest.TestCase):
    def test_original_search_and_cli_parity(self):
        original = original_module()
        for statement, statuses, returncode in [
            (POLICY, ("Theorem",), 0),
            (POLICY, ("Unsatisfiable",), 9),
            (POLICY, ("ContradictoryAxioms",), 7),
            (SUBSET, ("GaveUp", "Theorem"), 0),
            (SUBSET, ("GaveUp", "GaveUp"), 0),
            (SUBSET, ("Theorem", "GaveUp"), 0),
        ]:
            with (
                self.subTest(statuses=statuses, statement=statement),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory).resolve()
                with environment(
                    root, statement, statuses=statuses, returncode=returncode
                ) as (compiler, artifact):
                    reports, histories, files = [], [], []
                    for discover in [original.discover_proof, v.discover_proof]:
                        shutil.rmtree(artifact, ignore_errors=True)
                        compiler.reset_calls()
                        compiler.versions = 0
                        reports.append(
                            clean(
                                discover(
                                    statement, artifact_root=artifact, time_limit=10
                                )
                            )
                        )
                        histories.append(clean(deepcopy(compiler.calls)))
                        files.append(
                            {
                                p.name: (
                                    clean(json.loads(p.read_text()))
                                    if p.suffix == ".json"
                                    else clean(p.read_text())
                                )
                                for p in artifact.iterdir()
                            }
                        )
                        self.assertEqual(compiler.versions, 1)
                    self.assertEqual(*reports)
                    self.assertEqual(*histories)
                    self.assertEqual(*files)
                    expected = (
                        2 if statuses[0] == "GaveUp" and statement == SUBSET else 1
                    )
                    self.assertEqual(reports[0]["attempt_count"], expected)
                    compiler.reset_calls()
                    with contextlib.redirect_stdout(io.StringIO()):
                        if statuses[-1] == "GaveUp" and statuses[0] == "GaveUp":
                            with self.assertRaises(TypeError):
                                tools.source().main()
                        else:
                            self.assertEqual(tools.source().main(), 0)

    def test_registered_production_service(self):
        import mcp_server

        names = asyncio.run(mcp_server.mcp.list_tools())
        names = {t.name for t in names}
        doc = yaml.safe_load(CONTRACT.read_text())
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("policy_normalization", path)
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        preserved = [d for d in normalizer.inventory() if d["id"] == doc["id"]]
        self.assertEqual(preserved, [doc])
        for operation in doc["operations"].values():
            self.assertIn(operation["execution"]["binding"]["target"], names)

    def test_real_lunar_paths(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc["id"], "hub_example_vampire_policy_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc["policy"]["limits"]["wall_time_seconds"], 180)
        self.assertEqual(doc["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(
            doc,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/vampire-policy.workflow.json"
                ).read_text()
            ),
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        async def scenario(
            statement=POLICY,
            statuses=("Theorem",),
            returncode=0,
            dry=False,
            failure=None,
            empty_proof=False,
            unexpected_write=False,
            unsupported=False,
            bound=False,
            missing_binary=False,
            preflight_failure=False,
            write_report=False,
        ):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                with environment(
                    root,
                    statement,
                    statuses=statuses,
                    returncode=returncode,
                    failure=failure,
                    empty_proof=empty_proof,
                    unexpected_write=unexpected_write,
                ) as (compiler, artifact):
                    if preflight_failure:
                        (root / "examples/vampire_informal_to_proofs.py").unlink()
                    server = FastMCP("policy-fixture")
                    sessions = tools.register_vampire_policy_tools(server)
                    async with create_connected_server_and_client_session(
                        server
                    ) as client:
                        initialized = await client.initialize()
                        remote = RemoteSession(client, initialized)
                        inventory = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]
                        document = deepcopy(doc)
                        if bound:
                            document["flow"]["steps"][2]["max_iterations"] = 1
                        snapshot = assets(document)
                        compiled = compile_workflow(
                            "mcp:policy-fixture",
                            workflow_documents([DESCRIPTOR], snapshot)[0],
                            inventory,
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(doc["operations"])
                        )
                        self.assertTrue(compiled["runtime_source"])

                        async def authorize():
                            pass

                        # Missing binary is solely external resolver failure, before directory creation.
                        with contextlib.ExitStack() as stack:
                            if missing_binary:
                                stack.enter_context(
                                    patch.dict(os.environ, {"VAMPIRE_BIN": ""})
                                )
                                stack.enter_context(
                                    patch.object(v.shutil, "which", return_value=None)
                                )
                            result = await execute(
                                compiled,
                                snapshot,
                                {
                                    "context": {
                                        **CONTEXT,
                                        "dry_run": dry,
                                        "write_report": write_report,
                                    }
                                },
                                remote,
                                authorize,
                            )
                        if failure or unsupported or missing_binary or bound:
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertFalse(
                                (artifact / "discovery_report.json").exists()
                            )
                            self.assertEqual(
                                len(compiler.calls), 1 if (failure or bound) else 0
                            )
                            self.assertEqual(compiler.versions, 0)
                            if failure and write_report:
                                reports = list(
                                    (root / "artifacts/workflow_hub").glob("*.json")
                                )
                                self.assertEqual(len(reports), 1)
                                failed = json.loads(reports[0].read_text())
                                self.assertFalse(failed["ok"])
                                self.assertTrue(failed["write_audit"]["ok"])
                                self.assertIn(
                                    "deterministic compiler failure", failed["stderr"]
                                )
                            (
                                self.assertFalse(artifact.exists())
                                if missing_binary
                                else None
                            )
                            for session in sessions.values():
                                if "steps" in session:
                                    session["steps"].close()
                            return
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        self.assertEqual(len(sessions), 0)
                        if dry or preflight_failure:
                            self.assertFalse(compiler.calls)
                            self.assertFalse(artifact.exists())
                            self.assertEqual(len(result["calls"]), 5)
                            self.assertEqual(payload["ok"], not preflight_failure)
                            self.assertNotIn("write_audit", payload)
                            return
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        persisted = json.loads(
                            (artifact / "discovery_report.json").read_text()
                        )
                        count = (
                            2 if statuses[0] == "GaveUp" and statement == SUBSET else 1
                        )
                        self.assertEqual(len(compiler.calls), count)
                        self.assertEqual(len(result["calls"]), 6 + count * 2)
                        self.assertEqual(persisted["attempt_count"], count)
                        self.assertEqual(
                            persisted["candidate_count"],
                            2 if statement == SUBSET else 1,
                        )
                        self.assertEqual(compiler.versions, 1)
                        self.assertFalse(persisted["premise_loop"]["enabled"])
                        self.assertEqual(
                            payload["write_audit"]["ok"], not unexpected_write, payload
                        )
                        if unexpected_write:
                            self.assertEqual(payload["status"], "undeclared_writes")
                            self.assertIn(
                                "unexpected.txt",
                                payload["write_audit"]["unexpected_paths"],
                            )
                        for attempt in persisted["attempts"]:
                            self.assertIsNone(attempt["premise_selection_report"])
                            self.assertEqual(
                                attempt["premise_minimization_attempts"], []
                            )
                            self.assertTrue(Path(attempt["problem_path"]).is_file())
                            self.assertTrue(Path(attempt["result_path"]).is_file())
                        proved = statuses[count - 1] != "GaveUp"
                        self.assertEqual(persisted["ok"], proved)
                        self.assertEqual(
                            payload["returncode"],
                            (0 if proved and not empty_proof else 3 if proved else 1),
                        )
                        self.assertEqual(
                            payload["ok"],
                            proved and not empty_proof and not unexpected_write,
                        )
                        if not proved:
                            self.assertIsNone(persisted["winner"])
                            self.assertIsNone(persisted["winning_informal_proof"])
                            self.assertIn("TypeError", payload["stderr"])
                        if proved and returncode:
                            self.assertFalse(persisted["attempts"][-1]["result"]["ok"])
                            self.assertTrue(persisted["ok"])
                        if write_report:
                            self.assertTrue(Path(payload["report_file"]).is_file())
                        histories = deepcopy(compiler.calls)
                        compiler.reset_calls()
                        with contextlib.redirect_stdout(io.StringIO()) as stdout:
                            try:
                                original_code = tools.source().main()
                            except TypeError:
                                original_code = 1
                        original_report = json.loads(
                            (artifact / "discovery_report.json").read_text()
                        )
                        self.assertEqual(payload["returncode"], original_code)
                        self.assertEqual(payload["stdout"], stdout.getvalue())
                        self.assertEqual(clean(persisted), clean(original_report))
                        self.assertEqual(clean(histories), clean(compiler.calls))

        cases = [
            dict(),
            dict(dry=True),
            dict(preflight_failure=True),
            dict(write_report=True),
            dict(unexpected_write=True),
            dict(statuses=("Unsatisfiable",), returncode=8),
            dict(statuses=("ContradictoryAxioms",)),
            dict(empty_proof=True),
            dict(statuses=("GaveUp",)),
            dict(statement=SUBSET, statuses=("GaveUp", "Theorem")),
            dict(statement=SUBSET, statuses=("Theorem", "GaveUp")),
            dict(statement=SUBSET, statuses=("GaveUp", "GaveUp")),
            dict(statement=SUBSET, statuses=("GaveUp", "Theorem"), bound=True),
            dict(
                failure=RuntimeError("deterministic compiler failure"),
                write_report=True,
            ),
            dict(statement="unsupported statement", unsupported=True),
            dict(missing_binary=True),
        ]
        for case in cases:
            with self.subTest(case=case):
                asyncio.run(scenario(**case))

    def test_continuation_replay_and_guard(self):
        async def scenario():
            with (
                tempfile.TemporaryDirectory() as directory,
                environment(Path(directory).resolve()) as (compiler, artifact),
            ):
                server = FastMCP("continuations")
                sessions = tools.register_vampire_policy_tools(server)

                async def call(name, **arguments):
                    return (
                        await server.call_tool("mathformer_policy_" + name, arguments)
                    )[1]

                plan = (await call("preflight", context=CONTEXT))["plan"]
                statement = (await call("read_statement", plan=plan))["statement"]
                state = (await call("initialize", statement=statement, plan=plan))[
                    "state"
                ]
                self.assertEqual(state["evidence"], {"candidate_count": 1})
                attempt = (await call("direct_attempt", state=state))["attempt"]
                self.assertTrue(attempt["evidence"]["proof_found"])
                with self.assertRaises(Exception):
                    await call("direct_attempt", state=state)
                carried = await call("carry", state=state, attempt=attempt)
                self.assertTrue(carried["done"])
                self.assertEqual(carried["state"]["evidence"]["attempt_count"], 1)
                self.assertIsNotNone(carried["state"]["evidence"]["winner"])
                with self.assertRaises(Exception):
                    await call("carry", state=state, attempt=attempt)
                report = (await call("write_report", state=carried["state"]))["report"]
                with self.assertRaises(Exception):
                    await call("write_report", state=carried["state"])
                outcome = (
                    await call("finish_example", statement=statement, report=report)
                )["outcome"]
                self.assertTrue(
                    (await call("audit", plan=plan, outcome=outcome))["result"]["ok"]
                )
                self.assertFalse(sessions)
                self.assertEqual(len(compiler.calls), 1)
                denied = FastMCP("denied")

                def guard():
                    raise PermissionError("service read-only")

                tools.register_vampire_policy_tools(denied, guard)
                with self.assertRaises(Exception):
                    await denied.call_tool(
                        "mathformer_policy_preflight", {"context": CONTEXT}
                    )
                dry = (
                    await denied.call_tool(
                        "mathformer_policy_preflight",
                        {"context": {**CONTEXT, "dry_run": True}},
                    )
                )[1]
                self.assertFalse(dry["plan"]["execute"])

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main(verbosity=2)
