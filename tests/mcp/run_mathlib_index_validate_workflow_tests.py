#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native stamp validation over registered MCP tools and real Lunar/PRISM runtime.

Only the external Lean/Git version subprocess boundary is replaced. No model,
provider, external compiler, credential or production index is used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
# Production server registrations also import the project's scientific libraries.
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml
from mathlib_index_validation_tools import source

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathlib_index_validate_workflow/workflow.yaml"


def boundary(settings, calls):
    """Deterministic fixture at the actual process boundary; preserves native wrapper."""

    def run(command, **kwargs):
        calls(command, kwargs)
        values = settings()
        if values.get("error") == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if values.get("error") == "os":
            raise OSError("deterministic launch failure")
        key = "git" if command[0] == "git" else "lean"
        return SimpleNamespace(
            stdout=values.get(key, "") + "\nignored second line\n",
            stderr="",
            returncode=0,
        )

    return SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def fixture_server(control, log):
    # Import real production registration, then replace only the version process
    # interface in the source common module. There is no production fixture mode.
    from mcp_server import mcp

    source()
    common = sys.modules["mathlib_index_common"]

    def record(command, kwargs):
        with Path(log).open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "command": command,
                        "cwd": str(kwargs["cwd"]),
                        "timeout": kwargs["timeout"],
                        "check": kwargs["check"],
                    }
                )
                + "\n"
            )

    common.subprocess = boundary(lambda: json.loads(Path(control).read_text()), record)
    mcp.run(transport="stdio")


def oracle():
    path = ROOT / "tests/mcp/fixtures/mathlib_index_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "mathlib_index_oracle", SourceFileLoader("mathlib_index_oracle", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class ValidationTests(unittest.TestCase):
    def test_native_original_equivalence_and_process_semantics(self):
        native = source()
        original = oracle()
        common = sys.modules["mathlib_index_common"]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, output = base / "repo/Mathlib", base / "index.json"
            calls = []
            values = {"lean": "Lean fixture", "git": "rev fixture"}
            process = boundary(
                lambda: values, lambda command, kwargs: calls.append((command, kwargs))
            )
            args = native.parse_args(
                [
                    "--validate-existing",
                    "--json",
                    "--mathlib-root",
                    str(root),
                    "--output",
                    str(output),
                ]
            )
            with patch.object(common, "subprocess", process):
                for state in (
                    "missing_root",
                    "missing_index",
                    "matching",
                    "stale",
                    "timeout",
                    "os",
                    "bad_shape",
                    "bad_json",
                    "bad_utf8",
                ):
                    with self.subTest(state=state):
                        if state == "missing_index":
                            root.mkdir(parents=True)
                        if state == "matching":
                            (root.parent / ".git").mkdir()
                            output.write_text(
                                json.dumps(
                                    {
                                        "version_stamp": {
                                            "lean_version": "Lean fixture",
                                            "mathlib_git_revision": "rev fixture",
                                            "build_timestamp_utc": "ignored",
                                        },
                                        "declarations": ["irrelevant"],
                                    }
                                )
                            )
                        if state == "stale":
                            output.write_text('{"version_stamp":{}}')
                        if state in ("timeout", "os"):
                            values["error"] = state
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
                        if state == "bad_shape":
                            output.write_text("[]")
                        if state == "bad_json":
                            output.write_text("{")
                        if state == "bad_utf8":
                            output.write_bytes(b"\xff")
                        if state.startswith("bad_"):
                            error = {
                                "bad_shape": AttributeError,
                                "bad_json": json.JSONDecodeError,
                                "bad_utf8": UnicodeDecodeError,
                            }[state]
                            with self.assertRaises(error):
                                original.build(args)
                            with self.assertRaises(error):
                                native.build(args)
                            continue
                        calls.clear()
                        expected = original.build(args)
                        original_calls = list(calls)
                        calls.clear()
                        self.assertEqual(native.build(args), expected)
                        self.assertEqual(calls, original_calls)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = native.main(
                                [
                                    "--validate-existing",
                                    "--json",
                                    "--mathlib-root",
                                    str(root),
                                    "--output",
                                    str(output),
                                ]
                            )
                        self.assertEqual(code, 0 if expected["ok"] else 1)
                        self.assertEqual(json.loads(stream.getvalue()), expected)
                        if state in ("missing_root", "missing_index"):
                            self.assertEqual(calls, [])
                        else:
                            self.assertEqual(
                                [c[0][0] for c in original_calls], ["git", "lean"]
                            )
                            self.assertTrue(
                                all(
                                    c[1]["timeout"] == 20 and c[1]["check"] is False
                                    for c in calls
                                )
                            )
                # Absent .git skips only Git, and only two stamp fields matter.
                (root.parent / ".git").rmdir()
                values.clear()
                values["lean"] = "Lean fixture"
                output.write_text(
                    '{"version_stamp":{"lean_version":"Lean fixture","mathlib_git_revision":"unknown"},"modules":null}'
                )
                calls.clear()
                self.assertTrue(native.build(args)["ok"])
                self.assertEqual([c[0] for c in calls], [["lean", "--version"]])
                self.assertEqual(
                    output.read_text(),
                    '{"version_stamp":{"lean_version":"Lean fixture","mathlib_git_revision":"unknown"},"modules":null}',
                )

    def test_registered_tools_real_prism_compiler_and_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from mcp_connections.client import SessionManager
        from mcp_connections.models import StdioConfig
        from mcp_connections.contracts import workflow_documents
        from mcp_connections.workflow_compiler import compile_workflow
        from mcp_connections.execution import execute

        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_mathlib_index_validate_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 4)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, output = base / "repo/Mathlib", base / "index.json"
            control, log = base / "versions.json", base / "calls.jsonl"
            control.write_text(
                json.dumps({"lean": "Lean fixture", "git": "revision fixture"})
            )
            manager = SessionManager()
            async with manager.open(
                "mathlib-fixture",
                StdioConfig(
                    command=sys.executable,
                    args=[
                        str(Path(__file__).resolve()),
                        "--serve-version-fixture",
                        str(control),
                        str(log),
                    ],
                    cwd=str(ROOT),
                ),
                {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
            ) as remote:
                tools = [
                    tool.model_dump(by_alias=True, exclude_none=True)
                    for tool in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    compiled = compile_workflow(
                        "mcp:mathlib-fixture", selected, inventory
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(doc=document):
                    selected, received = (
                        (compiled, assets) if doc is document else compile(doc)
                    )
                    return await execute(
                        selected,
                        received,
                        {"mathlib_root": str(root), "output": str(output)},
                        remote,
                        authorize,
                    )

                async def accepted(expected, names):
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        ["mathformer_mathlib_index_" + n for n in names],
                    )
                    self.assertTrue(result["replay_artifacts"])
                    return result

                native = source()
                await accepted(
                    native.missing_root(root), ["root_exists", "missing_root"]
                )
                self.assertFalse(log.exists())
                root.mkdir(parents=True)
                await accepted(
                    native.missing_index(output),
                    ["root_exists", "index_exists", "missing_index"],
                )
                self.assertFalse(log.exists())
                names = [
                    "root_exists",
                    "index_exists",
                    "load_index",
                    "compare_and_return",
                ]
                for git_present, error, stale in [
                    (False, None, False),
                    (True, None, False),
                    (True, None, True),
                    (True, "timeout", False),
                    (True, "os", False),
                ]:
                    if git_present:
                        (root.parent / ".git").mkdir(exist_ok=True)
                    control.write_text(
                        json.dumps(
                            {
                                "lean": "Lean fixture",
                                "git": "revision fixture",
                                "error": error,
                            }
                        )
                    )
                    version = (
                        "unavailable:TimeoutExpired"
                        if error == "timeout"
                        else "unavailable:OSError" if error else None
                    )
                    stamp = {
                        "lean_version": version or "Lean fixture",
                        "mathlib_git_revision": version
                        or ("revision fixture" if git_present else "unknown"),
                        "build_timestamp_utc": "not compared",
                        "file_count": 999,
                    }
                    if stale:
                        stamp["lean_version"] = "different"
                    output.write_text(
                        json.dumps({"version_stamp": stamp, "declarations": None})
                    )
                    before = output.read_bytes()
                    log.unlink(missing_ok=True)
                    await accepted(
                        {
                            "ok": not stale,
                            "style": "mathlib_index_validation",
                            "output": str(output),
                            "stale": stale,
                            "version_stamp": stamp,
                        },
                        names,
                    )
                    records = [
                        json.loads(line) for line in log.read_text().splitlines()
                    ]
                    self.assertEqual(
                        [r["command"] for r in records],
                        ([["git", "rev-parse", "HEAD"]] if git_present else [])
                        + [["lean", "--version"]],
                    )
                    self.assertTrue(
                        all(r["timeout"] == 20 and r["check"] is False for r in records)
                    )
                    self.assertEqual(output.read_bytes(), before)
                for content, count in [
                    (b"{", 3),
                    (b"\xff", 3),
                    (b"[]", 4),
                    (b'{"version_stamp":null}', 4),
                ]:
                    output.write_bytes(content)
                    failed = await run()
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), count)
                    self.assertEqual(failed["calls"][-1]["status"], "rejected")
                output.write_text("{}")
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 2
                log.unlink(missing_ok=True)
                failed = await run(bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(failed).lower())
                self.assertFalse(log.exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                selected, received = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        selected,
                        received,
                        {"mathlib_root": str(root), "output": str(output)},
                        remote,
                        pending,
                    )
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve-version-fixture":
        fixture_server(*sys.argv[2:])
    else:
        unittest.main(verbosity=2)
