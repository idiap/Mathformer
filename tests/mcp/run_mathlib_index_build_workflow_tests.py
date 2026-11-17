#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Mathlib build steps, production MCP registration and real Lunar/PRISM.

WORKFLOW_CONTRACT_PATH explicitly selects the candidate or installed contract.
No providers, credentials, external compilers or production artifacts are used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
PYTHON = LUNAR / ".venv/bin/python"
if PYTHON.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(PYTHON), [str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(Path(__file__).parent / "fixtures"),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import asynccontextmanager, redirect_stdout
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml

from mathlib_index_build_tools import native_args, source
from mathlib_index_build_boundary import lean_tree, serve, version_process

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathlib_index_build_workflow/workflow.yaml"
PREFIX = "mathformer_mathlib_index_build_"


def oracle():
    path = ROOT / "tests/mcp/fixtures/mathlib_index_build_original.py.txt"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "e77536c55db29ba00645456e9d32cb703da94f0261f32aea89d371b33e9ae0f8"
    )
    spec = importlib.util.spec_from_loader(
        "mathlib_build_oracle", SourceFileLoader("mathlib_build_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transport_args(root, output, cache, max_files=None, validate=False):
    return {
        "mathlib_root": str(root),
        "output": str(output),
        "reranker_cache": str(cache),
        "max_files": max_files,
        "validate_existing": validate,
    }


def assets(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


@asynccontextmanager
async def fixture_session(manager, key, config):
    # Preserve assertion diagnostics: SessionManager otherwise wraps body errors
    # as transport failures. This does not replace any transport/runtime code.
    error = None
    async with manager.open(key, config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}) as remote:
        try:
            yield remote
        except Exception as exc:
            error = exc
    if error is not None:
        raise error


def stable(value):
    """Ignore only native wall-clock fields and the hashes derived from them."""
    if isinstance(value, (list, tuple)):
        return [stable(item) for item in value]
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key not in {"build_timestamp_utc", "metadata_hash", "source_index_hash"}
        }
    return value


class BuildWorkflowTests(unittest.TestCase):
    def check_artifacts(self, output, cache):
        index, reranker = json.loads(output.read_text()), json.loads(cache.read_text())
        stamp = index["version_stamp"]
        datetime.fromisoformat(stamp["build_timestamp_utc"].replace("Z", "+00:00"))
        expected_hash = hashlib.sha256(
            json.dumps(stamp, sort_keys=True).encode()
        ).hexdigest()[:16]
        self.assertEqual(index["metadata_hash"], expected_hash)
        self.assertEqual(reranker["source_index_hash"], expected_hash)
        for path, value in [(output, index), (cache, reranker)]:
            self.assertEqual(
                path.read_text(), json.dumps(value, indent=2, sort_keys=True)
            )
        self.assertEqual(stamp["file_count"], len(index["modules"]))
        self.assertEqual(stamp["declaration_count"], len(index["declarations"]))
        self.assertEqual(reranker["entry_count"], len(reranker["entries"]))
        self.assertTrue(
            all(
                row["lean_check_status"] == "unverified"
                for row in index["declarations"]
            )
        )
        self.assertTrue(
            all(
                len(neighbors) <= 12 and neighbors == sorted(neighbors)
                for neighbors in index["declaration_graph"].values()
            )
        )
        return index, reranker

    def test_original_entrypoint_equivalence_and_native_failure_order(self):
        native, original = source(), oracle()
        common = sys.modules["mathlib_index_common"]
        settings, calls = {"lean": "Lean fixture", "git": "revision fixture"}, []
        process = version_process(
            lambda: settings, lambda command, kwargs: calls.append((command, kwargs))
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(common, "subprocess", process),
        ):
            base = Path(directory)
            root, output, cache = (
                base / "repo/Mathlib",
                base / "out/index.json",
                base / "cache/cache.json",
            )
            args = transport_args(root, output, cache)
            self.assertEqual(
                native.build(native_args(args)), original.build(native_args(args))
            )
            self.assertEqual(calls, [])
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = native.main(["--mathlib-root", str(root), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(stream.getvalue()), native.missing_root(root))
            lean_tree(root)
            (root.parent / ".git").mkdir()
            for cap, count in [(None, 4), (0, 0), (1, 1), (-1, 3), (99, 4)]:
                with self.subTest(max_files=cap):
                    args["max_files"] = cap
                    calls.clear()
                    expected = original.build(native_args(args))
                    before = self.check_artifacts(output, cache)
                    expected_calls = list(calls)
                    calls.clear()
                    actual = native.build(native_args(args))
                    self.assertEqual(stable(actual), stable(expected))
                    self.assertEqual(
                        stable(self.check_artifacts(output, cache)), stable(before)
                    )
                    self.assertEqual(actual["module_count"], count)
                    self.assertEqual(calls, expected_calls)
                    self.assertEqual(
                        [c[0] for c in calls],
                        [["git", "rev-parse", "HEAD"], ["lean", "--version"]],
                    )
                    self.assertTrue(
                        all(
                            c[1]["timeout"] == 20 and c[1]["check"] is False
                            for c in calls
                        )
                    )
            args["max_files"] = None
            cli = [
                "--mathlib-root",
                str(root),
                "--output",
                str(output),
                "--reranker-cache",
                str(cache),
                "--json",
            ]
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = native.main(cli)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue())["declaration_count"], 28)
            args["validate_existing"] = True
            for state in (
                "matching",
                "stale",
                "timeout",
                "os",
                "bad_json",
                "bad_utf8",
                "bad_shape",
                "missing_index",
            ):
                with self.subTest(state=state):
                    if state == "stale":
                        output.write_text('{"version_stamp":{}}')
                    if state in ("timeout", "os"):
                        settings["error"] = state
                        version = (
                            "unavailable:TimeoutExpired"
                            if state == "timeout"
                            else "unavailable:OSError"
                        )
                        output.write_text(
                            json.dumps(
                                {
                                    "version_stamp": {
                                        "lean_version": version,
                                        "mathlib_git_revision": version,
                                    }
                                }
                            )
                        )
                    if state == "bad_json":
                        output.write_text("{")
                    if state == "bad_utf8":
                        output.write_bytes(b"\xff")
                    if state == "bad_shape":
                        output.write_text("[]")
                    if state == "missing_index":
                        output.unlink()
                    if state.startswith("bad_"):
                        error = {
                            "bad_json": json.JSONDecodeError,
                            "bad_utf8": UnicodeDecodeError,
                            "bad_shape": AttributeError,
                        }[state]
                        with self.assertRaises(error):
                            original.build(native_args(args))
                        with self.assertRaises(error):
                            native.build(native_args(args))
                    else:
                        self.assertEqual(
                            native.build(native_args(args)),
                            original.build(native_args(args)),
                        )
            settings.pop("error")
            args["validate_existing"] = False
            # The second write fails after index.json has already been replaced.
            blocked = base / "blocked"
            blocked.write_text("file, not directory")
            args["reranker_cache"] = str(blocked / "cache.json")
            for implementation in (original, native):
                output.unlink(missing_ok=True)
                with self.assertRaises(FileExistsError):
                    implementation.build(native_args(args))
                self.assertTrue(output.exists())
                self.assertEqual(
                    json.loads(output.read_text())["version_stamp"]["file_count"], 4
                )
                self.assertFalse((blocked / "cache.json").exists())

    def test_graph_bounds_and_reranker_exhaustion(self):
        native = source()
        common = sys.modules["mathlib_index_common"]
        # Distinct modules/namespaces isolate the token-peer scan and its stop.
        # Later peers sort before earlier peers, so removing either scan bound
        # would change the retained neighbors even after final sorted truncation.
        declarations = [
            {
                "qualified_name": f'{"Z" if i<13 else "A"}{i:02d}.compact',
                "module": f"M{i}",
                "namespace": f"N{i}",
                "declaration_tokens": ["compact"],
            }
            for i in range(20)
        ]
        graph = common.build_declaration_graph(declarations)
        self.assertEqual(
            graph["Z00.compact"], [f"Z{i:02d}.compact" for i in range(1, 13)]
        )
        self.assertNotIn("A13.compact", graph["Z00.compact"])
        # Without a token peer, only the first 16 module/namespace peers matter.
        for i, item in enumerate(declarations):
            item.update(
                qualified_name=f'{"Z" if i<16 else "A"}{i:02d}.plain',
                module="M",
                namespace="N",
                declaration_tokens=[],
            )
        graph = common.build_declaration_graph(declarations)
        self.assertEqual(graph["A19.plain"], [f"Z{i:02d}.plain" for i in range(12)])
        self.assertEqual(common.build_declaration_graph([]), {})
        self.assertEqual(
            native.build_optional_reranker_cache(
                {"declarations": [], "metadata_hash": "h"}
            )["entries"],
            [],
        )
        cache = native.build_optional_reranker_cache(
            {
                "metadata_hash": "h",
                "declarations": [
                    {"doc_comment": "", "namespace_tokens": []},
                    {
                        "qualified_name": "N.x",
                        "module": "M",
                        "doc_comment": "hello hello",
                        "namespace_tokens": ["N"],
                    },
                ],
            }
        )
        self.assertEqual(cache["entry_count"], 1)
        row = cache["entries"][0]
        bucket = str(int(hashlib.sha256(b"hello").hexdigest()[:8], 16) % 64)
        self.assertEqual(row["doc_comment_token_hash_embedding"], {bucket: 2.0})
        self.assertFalse(cache["enabled_by_default"])

    def test_registered_tools_lunar_compile_and_real_prism_runtime(self):
        asyncio.run(self.scenarios())

    async def scenarios(self):
        from mcp_connections.client import SessionManager
        from mcp_connections.models import StdioConfig
        from mcp_connections.contracts import workflow_documents
        from mcp_connections.workflow_compiler import compile_workflow
        from mcp_connections.execution import execute

        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        authored = (
            ROOT
            / "skills/control/workflow-contract-validator/references/mathlib-index-build.workflow.json"
        )
        self.assertEqual(document, json.loads(authored.read_text()))
        self.assertEqual(document["id"], "hub_mathlib_index_build_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 300, "max_operation_calls": 5},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertTrue(
            all(
                op["execution"]["mode"] == "deterministic"
                for op in document["operations"].values()
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, output, cache = (
                base / "repo/Mathlib",
                base / "out/index.json",
                base / "out/cache.json",
            )
            control, log = base / "versions.json", base / "calls.jsonl"
            settings = {"lean": "Lean fixture", "git": "revision fixture"}
            control.write_text(json.dumps(settings))
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[
                    str(Path(__file__).resolve()),
                    "--serve-version-fixture",
                    str(control),
                    str(log),
                    str(base),
                ],
                cwd=str(ROOT),
            )
            async with fixture_session(manager, "build-fixture", config) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    received = assets(doc)
                    selected = workflow_documents([DESCRIPTOR], received)[0]
                    compiled = compile_workflow(
                        "mcp:build-fixture", selected, inventory
                    )
                    return compiled, received

                compiled, received = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])
                for binding in document["operations"].values():
                    name = binding["execution"]["binding"]["target"]
                    self.assertFalse(
                        compile(document, [t for t in tools if t["name"] != name])[0][
                            "runnable"
                        ]
                    )

                async def authorize():
                    pass

                async def run(args, doc=document):
                    selected, snapshot = (
                        (compiled, received) if doc is document else compile(doc)
                    )
                    return await execute(
                        selected, snapshot, {"args": args}, remote, authorize
                    )

                async def accepted(args, names):
                    result = await run(args)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + n for n in names],
                    )
                    self.assertTrue(result["replay_artifacts"])
                    return result["outputs"]["result"]

                args = transport_args(root, output, cache)
                self.assertEqual(
                    await accepted(args, ["path_exists", "missing_root"]),
                    source().missing_root(root),
                )
                self.assertFalse(log.exists())
                root.mkdir(parents=True)
                validation = {**args, "validate_existing": True}
                self.assertEqual(
                    await accepted(
                        validation, ["path_exists", "path_exists", "missing_index"]
                    ),
                    source().missing_index(output),
                )
                self.assertFalse(log.exists())
                # Exhaustion of an empty tree is a successful empty index.
                payload = await accepted(
                    args, ["path_exists", "parse", "rerank", "write_return"]
                )
                index, reranker = self.check_artifacts(output, cache)
                self.assertEqual(
                    (
                        payload["module_count"],
                        payload["declaration_count"],
                        reranker["entries"],
                    ),
                    (0, 0, []),
                )
                self.assertEqual(
                    index["version_stamp"]["mathlib_git_revision"], "unknown"
                )
                names = lean_tree(root)
                (root.parent / ".git").mkdir()
                process = version_process(lambda: settings, lambda *a: None)
                common = sys.modules["mathlib_index_common"]
                for cap, expected_count in [
                    (None, 4),
                    (0, 0),
                    (1, 1),
                    (-1, 3),
                    (99, 4),
                ]:
                    with self.subTest(cap=cap):
                        inputs = {**args, "max_files": cap}
                        with patch.object(common, "subprocess", process):
                            expected = oracle().build(native_args(inputs))
                        expected_artifacts = self.check_artifacts(output, cache)
                        log.unlink(missing_ok=True)
                        payload = await accepted(
                            inputs, ["path_exists", "parse", "rerank", "write_return"]
                        )
                        index, reranker = self.check_artifacts(output, cache)
                        self.assertEqual(stable(payload), stable(expected))
                        self.assertEqual(stable(index), stable(expected_artifacts[0]))
                        self.assertEqual(
                            stable(reranker), stable(expected_artifacts[1])
                        )
                        self.assertEqual(payload["module_count"], expected_count)
                        selected_names = names if cap is None else names[:cap]
                        self.assertEqual(
                            [r["source_ref"] for r in index["modules"]], selected_names
                        )
                        records = [
                            json.loads(line) for line in log.read_text().splitlines()
                        ]
                        self.assertEqual(
                            [r["command"] for r in records],
                            [["git", "rev-parse", "HEAD"], ["lean", "--version"]],
                        )
                        self.assertTrue(
                            all(
                                r["timeout"] == 20 and r["check"] is False
                                for r in records
                            )
                        )
                        self.assertEqual(
                            [r["cwd"] for r in records], [str(root.parent), str(ROOT)]
                        )
                modules = {row["module"]: row for row in index["modules"]}
                self.assertEqual(
                    modules["Mathlib.Algebra.Base"]["direct_imports"],
                    ["Mathlib.Init", "Mathlib.External"],
                )
                self.assertEqual(
                    modules["Mathlib.Algebra.Base"]["imported_by"],
                    ["Mathlib.Algebra.Base.Child", "Mathlib.Z"],
                )
                self.assertEqual(modules["Mathlib.Algebra.Base"]["leaf_count"], 2)
                first = next(
                    row
                    for row in index["declarations"]
                    if row["qualified_name"] == "Mathlib.Algebra.Base.compact_first"
                )
                self.assertEqual(
                    (first["line"], first["source_ref"], first["doc_comment"]),
                    (
                        3,
                        "Algebra/Base.lean:3",
                        "import Mathlib.Init Mathlib.External /-- A compact fixture document",
                    ),
                )
                self.assertEqual(first["theorem_shape"]["proposition_kind"], "equality")
                self.assertEqual(index["declarations"][-1]["short_name"], "convex_last")
                dense = index["declaration_graph"]["Mathlib.Dense.compact_23"]
                self.assertEqual(
                    dense,
                    ["Mathlib.Algebra.Base.compact_first"]
                    + [f"Mathlib.Dense.compact_{i:02d}" for i in range(11)],
                )
                for error, stale in [
                    (None, False),
                    (None, True),
                    ("timeout", False),
                    ("os", False),
                ]:
                    settings["error"] = error
                    control.write_text(json.dumps(settings))
                    version = (
                        "unavailable:TimeoutExpired"
                        if error == "timeout"
                        else "unavailable:OSError" if error else None
                    )
                    stamp = {
                        "lean_version": (
                            "different" if stale else version or settings["lean"]
                        ),
                        "mathlib_git_revision": version or settings["git"],
                        "file_count": 999,
                        "build_timestamp_utc": "ignored",
                    }
                    output.write_text(
                        json.dumps({"version_stamp": stamp, "declarations": None})
                    )
                    before = (output.read_bytes(), cache.read_bytes())
                    payload = await accepted(
                        validation, ["path_exists", "path_exists", "load_validate"]
                    )
                    self.assertEqual(
                        payload,
                        {
                            "ok": not stale,
                            "stale": stale,
                            "style": "mathlib_index_validation",
                            "output": str(output),
                            "version_stamp": stamp,
                        },
                    )
                    self.assertEqual((output.read_bytes(), cache.read_bytes()), before)
                settings.pop("error")
                control.write_text(json.dumps(settings))
                for content in (b"{", b"[]", b"\xff", b'{"version_stamp":null}'):
                    output.write_bytes(content)
                    failed = await run(validation)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(
                        [c["tool"] for c in failed["calls"]],
                        [
                            PREFIX + n
                            for n in ["path_exists", "path_exists", "load_validate"]
                        ],
                    )
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                # Native read failure stops before version probes and persistence.
                (root / "Bad.lean").mkdir()
                before_cache = cache.read_bytes()
                log.unlink(missing_ok=True)
                failed = await run(args)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 2)
                self.assertEqual(cache.read_bytes(), before_cache)
                self.assertFalse(log.exists())
                (root / "Bad.lean").rmdir()
                # No rollback: the index survives failure creating the cache parent.
                blocked = base / "blocked"
                blocked.write_text("file")
                output.unlink()
                failed = await run(
                    {**args, "reranker_cache": str(blocked / "cache.json")}
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 4)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(
                    json.loads(output.read_text())["version_stamp"]["file_count"], 4
                )
                self.assertEqual(cache.read_bytes(), before_cache)
                # Service path policy checks both outputs before the first write.
                output.unlink()
                failed = await run(
                    {**args, "reranker_cache": str(base.parent / "outside-cache.json")}
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertFalse(output.exists())
                # Actual runtime operation budget stops before rerank/persistence.
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = 2
                failed = await run(args, limited)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(failed).lower())
                self.assertFalse(output.exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                selected, snapshot = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(selected, snapshot, {"args": args}, remote, pending)
            self.assertFalse(manager.active)
            readonly_config = config.model_copy(
                update={"args": config.args + ["readonly"]}
            )
            async with fixture_session(manager, "readonly", readonly_config) as remote:
                from mcp_connections.client import MCPConnectionError

                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "write_return",
                        {"args": args, "index": index, "cache": reranker},
                    )
                self.assertFalse(output.exists())
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve-version-fixture":
        serve(*sys.argv[2:5], readonly=len(sys.argv) > 5)
    else:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(BuildWorkflowTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(
            0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
        )
