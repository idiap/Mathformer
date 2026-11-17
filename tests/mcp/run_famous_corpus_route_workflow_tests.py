#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real route steps, MCP tools, Lunar PRISM compilation and runtime in fixtures.

No live model/provider, prover, credentials or production corpus run. Isolated
catalog data exercises the native generator, indexer and regression runner.
A separate compiler-boundary fixture exercises generic hub process failures.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import io
import json
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
from famous_corpus_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from famous_corpus_route_tree import (
    populate,
    put,
    stale,
    stable,
    LEAF,
    GENERATOR,
    INDEXER,
    ARTIFACT,
    TARGET,
)
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_kb_famous_corpus_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["famous", "corpus"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "dispatch", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/famous_corpus_route_original.py.txt").read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
        for path, content in values.items()
    ]


def comparable(result):
    result = deepcopy(result)
    for child in result["children"]:
        if child.get("stdout"):
            child["stdout"] = stable(json.loads(child["stdout"]))
    return result


def assert_corpus(test, root, child, success=True):
    payload = json.loads(child["stdout"])
    test.assertEqual(payload["ok"], success)
    test.assertEqual(child["returncode"], 0 if success else 3)
    test.assertEqual(payload["artifact_root"], str(root / ARTIFACT))
    test.assertEqual(payload["target_distance"]["entry_id"], TARGET)
    test.assertLess(
        payload["target_distance"]["cosine_distance"],
        payload["unrelated_distance"]["cosine_distance"],
    )
    test.assertIn(TARGET, payload["top_hit_ids"])
    test.assertLessEqual(len(payload["top_hit_ids"]), 5)
    test.assertTrue(child["write_audit"]["ok"])
    test.assertEqual(child["write_audit"]["unexpected_paths"], [])
    test.assertFalse((root / ARTIFACT / "stale.txt").exists())
    entries = [
        json.loads(line)
        for line in (root / ARTIFACT / "famous_theorems_axioms_500.jsonl")
        .read_text()
        .splitlines()
    ]
    test.assertEqual(len(entries), 500)
    test.assertEqual(entries[0]["id"], TARGET)
    test.assertTrue(
        all(
            e["status"] == "generated_candidate" and e["canonical_hashes"]["informal"]
            for e in entries
        )
    )
    test.assertTrue(all(not e["formal_statements"] for e in entries))
    test.assertTrue(all(e["provenance"][0]["kind"] == "generated" for e in entries))
    if success:
        test.assertTrue(all(payload["assertions"].values()), payload)
        test.assertEqual(len({e["id"] for e in entries}), 500)
    else:
        test.assertFalse(payload["assertions"]["all_ids_unique"])
        test.assertFalse(payload["assertions"]["indexer_added_500"])


class FamousCorpusRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_bindings_policy_and_provenance(self):
        module = load(
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
            "famous_normalizer",
        )
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.famous_corpus_route_descriptor(), document)
        self.assertEqual(document["id"], "route_kb_famous_corpus_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["effects"],
            {
                "filesystem": {
                    "read": ["repository", "native_runtime_inputs"],
                    "write": ["artifacts/kb/", "artifacts/workflow_hub/"],
                },
                "network": [],
                "external_write": [],
            },
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertTrue(
            any(
                r["path"] == "scripts/mathformer.py"
                and r["selector"] == "run_intent_match"
                for r in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", LEAF, "--json"))
        self.assertEqual(item.safety, "writes_artifacts")
        self.assertFalse(item.depends_on)
        self.assertFalse(item.allows_extra_args)
        self.assertIsNone(item.timeout_seconds)

    def test_original_state_and_stopping_semantics(self):
        oracle = original()
        native, match = checked_registry(REGISTRY), selected_match(MATCH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for dry in [False, True]:
                for keep in [False, True]:
                    ctx = hub.RunContext(dry_run=dry, keep_going=keep)
                    self.assertEqual(
                        oracle.run_intent_match(
                            match, native, ctx, repository_root=root
                        ),
                        hub.run_intent_match(match, native, ctx, repository_root=root),
                    )
            self.assertFalse((root / "artifacts").exists())
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok", False)), "children": [child]}
                )
                self.assertTrue(done)
                check_state(updated)
                with self.assertRaises(ValueError):
                    check_state(updated, selecting=True)
            # Shared controller also retains sticky failure before exhaustion.
            state, done = hub.advance_intent_state(
                {"ok": False, "children": [{"ok": False}]},
                {"ok": True},
                hub.RunContext(keep_going=keep),
                3,
            )
            self.assertFalse(done)
            self.assertFalse(state["ok"])
            self.assertEqual(len(state["children"]), 2)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": False, "children": []})

    def test_native_generator_indexer_and_regression_exception_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root, ROOT)
            generator = load(root / GENERATOR, "fixture_famous_generator")
            entries = generator.build_entries(limit=500)
            self.assertEqual(len(entries), 500)
            self.assertEqual(len(generator.build_entries(limit=7)), 7)
            with self.assertRaisesRegex(ValueError, "only 500"):
                generator.build_entries(limit=501)
            state = generator.parse_seed([])["state"]
            state = generator.open_domain(state)
            self.assertEqual(len(state["names"]), 20)
            for i in range(20):
                result = generator.append_entry(state)
                self.assertEqual(result["done"], i == 19)
                self.assertEqual(result["state"]["name_index"], i + 1)
                self.assertEqual(len(state["entries"]), i)
                state = result["state"]
            self.assertEqual(len(state["entries"]), 20)
            self.assertEqual(
                generator.advance_domain(state)["state"]["domain_index"], 1
            )
            indexer = load(root / INDEXER, "fixture_famous_indexer")
            seed = put(
                root,
                "fixture.jsonl",
                "".join(json.dumps(e.to_dict()) + "\n" for e in entries[:3]),
            )
            state = indexer.initialize(
                [
                    "--kb-root",
                    str(root / "fixture_kb"),
                    "--seed-jsonl",
                    str(seed),
                    "--build-bloom",
                    "--build-embeddings",
                    "--embedding-dimension",
                    "256",
                    "--smoke-query",
                    "Fundamental theorem of algebra",
                    "--json",
                ]
            )
            self.assertEqual(
                (state["cursor"], len(state["files"]), state["vampire"]), (0, 1, False)
            )
            ingested = indexer.ingest_file(state)
            self.assertTrue(ingested["done"])
            state = ingested["state"]
            self.assertEqual(state["cursor"], 1)
            self.assertEqual(len(state["results"]), 3)
            state = indexer.build_bloom(state)
            state = indexer.build_embeddings(state)
            self.assertEqual(
                json.loads(Path(state["embedding_index"]).read_text())["dimension"], 256
            )
            state = indexer.search(state)
            self.assertLessEqual(len(state["smoke_hits"]), 5)
            # Actual malformed input and I/O failures, not substituted steps.
            regression = load(root / LEAF, "fixture_famous_regression")
            paths = regression.prepare(
                {"artifact_root": str(root / "fixture_regression")}
            )
            Path(paths["artifact_root"]).mkdir()
            Path(paths["corpus_path"]).write_text("{malformed JSON\n")
            with self.assertRaisesRegex(RuntimeError, "command failed"):
                regression.index(paths)
            with self.assertRaises(OSError):
                regression.prepare({"artifact_root": str(seed)})
            with self.assertRaises(KeyError):
                regression.probe(
                    {"kb_root": str(root / "empty_kb")}, {"smoke_hits": []}
                )
            payload = {
                "ok": False,
                "artifact_root": paths["artifact_root"],
                "top_hit_ids": [],
            }
            for json_output in [False, True]:
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(regression.emit(payload, 3, json_output), 3)
                if json_output:
                    self.assertEqual(json.loads(out.getvalue()), payload)
                else:
                    self.assertIn("ok: False", out.getvalue())

    def test_external_compiler_boundary_and_hub_failure_capture(self):
        # No external compiler belongs to this selected route. Exercise the
        # generic native launch/capture/audit boundary using a separate action.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    item = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                    else:
                        child = hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=root
                        )
                        self.assertEqual(child["ok"], mode == "success")
                        self.assertEqual(
                            child["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "success":
                            self.assertFalse(json.loads(child["stdout"])["ok"])
                        elif mode == "reject":
                            self.assertEqual(child["returncode"], 7)
                        elif mode == "write":
                            self.assertEqual(
                                child["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        elif mode == "timeout":
                            self.assertEqual(
                                (child["returncode"], child["stdout"], child["stderr"]),
                                (None, "partial", "deadline"),
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
            finally:
                hub.subprocess = saved

    def test_registered_mcp_lunar_prism_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "famous-corpus-route",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected_scenario(remote)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure

    async def connected_scenario(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            documents = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(documents[0]["validation"]["valid"], documents[0])
            compiled = compile_workflow("mcp:famous-corpus-route", documents[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(ORDER))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [
            t for t in tools if t["name"] != "mathformer_famous_corpus_route_dispatch"
        ]
        rejected = compile_workflow(
            "mcp:famous-corpus-route",
            workflow_documents([DESCRIPTOR], assets)[0],
            missing,
        )
        self.assertFalse(rejected["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, received = compile(changed) if changed else (compiled, assets)
            return await execute(workflow, received, inputs, remote, authorize)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext()),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for ready, dry in [
                (False, False),
                (False, True),
                (True, True),
                (True, False),
            ]:
                if ready:
                    populate(root, ROOT)
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"].update(dry_run=dry, keep_going=keep)
                    if ready:
                        stale(root)
                    before = hub.snapshot_repository(root)
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    actual = result["outputs"]["result"]
                    if not (ready and not dry):
                        self.assertEqual(hub.snapshot_repository(root), before)
                    else:
                        assert_corpus(self, root, actual["children"][0])
                        stale(root)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(comparable(actual), comparable(expected))
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_famous_corpus_route_" + op for op in ORDER],
                    )
                    self.assertEqual(len(actual["children"]), 1)
                    self.assertEqual(actual["ok"], ready)
                    self.assertEqual(actual["route"]["score"], MATCH["score"])
                    self.assertEqual(
                        actual["route"]["matched_terms"], MATCH["matched_terms"]
                    )
                    if ready and not dry:
                        self.assertEqual(
                            actual["children"][0]["argv"],
                            [sys.executable, LEAF, "--json"],
                        )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
            for mode in ["duplicate", "malformed", "absent"]:
                populate(root, ROOT, mode)
                for keep in [False, True]:
                    inputs = deepcopy(base)
                    inputs["context"]["keep_going"] = keep
                    stale(root)
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    output = result["outputs"]["result"]
                    self.assertFalse(output["ok"])
                    self.assertEqual(output["status"], "intent_run_failed")
                    self.assertEqual(len(output["children"]), 1)
                    child = output["children"][0]
                    self.assertTrue(child["write_audit"]["ok"])
                    if mode == "duplicate":
                        assert_corpus(self, root, child, success=False)
                    else:
                        self.assertEqual(child["returncode"], 1)
                        self.assertEqual(child["stdout"], "")
                        self.assertIn(
                            "command failed" if mode == "malformed" else "No KB entry",
                            child["stderr"],
                        )
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            for forged in ["registry", "match", "cursor"]:
                inputs, changed = deepcopy(base), None
                inputs["context"]["dry_run"] = True
                if forged == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged-command"]
                elif forged == "match":
                    inputs["match"]["route"]["title"] = "forged title"
                else:
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    result["calls"][-1]["operation"],
                    "dispatch" if forged == "registry" else "select",
                )
            unknown = await remote.call(
                "mathformer_famous_corpus_route_dispatch",
                {
                    "action": ACTION,
                    "context": vars(hub.RunContext(dry_run=True)),
                    "registry": {},
                    "repository_root": str(root),
                },
            )
            self.assertEqual(
                unknown,
                {
                    "child": {
                        "ok": False,
                        "status": "unknown_action",
                        "action_id": ACTION,
                    }
                },
            )
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            for limit in [1, 3, 4]:
                changed = deepcopy(document)
                changed["policy"]["limits"]["max_operation_calls"] = limit
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    limit,
                )
            changed = deepcopy(document)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            workflow, received = compile(timed)

            async def waiting_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(workflow, received, inputs, remote, waiting_authority)
            # Only dry-run is permitted against the actual repository.
            for omitted in [False, True]:
                inputs["repository_root"] = None
                if omitted:
                    inputs.pop("repository_root")
                result = await run(inputs)
                self.assertEqual(
                    result["outputs"],
                    {
                        "result": hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(dry_run=True),
                        )
                    },
                )


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
