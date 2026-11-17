#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native equivalence, real registered MCP tools, Lunar and PRISM execution.

Only the external Lake boundary is substituted. Every module check, transition,
report, argparse branch, filesystem effect and emission uses production source.
No provider/model participates in this deterministic verifier.
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
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import (
    asynccontextmanager,
    contextmanager,
    redirect_stdout,
    redirect_stderr,
)
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from foundation_verify_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_foundation_verify_workflow/workflow.yaml"
SELECTED = "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py"
LIB = Path("MathformerPhysicsLib/Lean/Foundations")
FIXTURES = ROOT / "tests/mcp/fixtures"
GOOD = "import Mathlib\n/-- Mathlib grounding: deterministic α fixture. -/\ndef n : Nat := 0\n"
BAD = "sorry\nadmit\naxiom bad : False\ndef vacuous : Prop := True\n"


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def oracle():
    return load(
        "foundation_verify_oracle", FIXTURES / "foundation_verify_original.py.txt"
    )


def fixture(root):
    (root / "fixture_repository").write_text("foundation-verifier-test")
    (root / LIB).mkdir(parents=True, exist_ok=True)


def module_file(root, name, text=GOOD):
    path = root / LIB / f"{name}.lean"
    path.write_text(text)
    return path


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def clean(root):
    for p in root.iterdir():
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
    fixture(root)


def compiler_calls(root):
    p = root / "compiler_calls.jsonl"
    return (
        [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []
    )


@contextmanager
def mount(module, root):
    with (
        patch.object(module, "REPO_ROOT", root),
        patch.object(module, "DEFAULT_MODULES", sorted((root / LIB).glob("*.lean"))),
    ):
        yield


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


@asynccontextmanager
async def diagnosed_session(manager, *args):
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class FoundationVerifyTests(unittest.TestCase):
    def test_native_entrypoint_equivalence(self):
        old = oracle()
        boundary = load(
            "foundation_verify_test_compiler",
            FIXTURES / "foundation_verify_compiler/sitecustomize.py",
        )
        # Importing sitecustomize installs its boundary; restore it for the parent.
        boundary.subprocess.run = boundary.native_run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for mode in (
                "valid",
                "blocked",
                "compile_failure",
                "empty",
                "launch_error",
                "missing",
                "output_error",
                "self_io_error",
            ):
                for flags in ([], ["--skip-index-compile"], ["--self-test"]):
                    for output, print_json in (
                        (False, False),
                        (True, False),
                        (True, True),
                    ):
                        with self.subTest(
                            mode=mode, flags=flags, output=output, json=print_json
                        ):
                            outcomes = []
                            for module in (old, source):
                                clean(root)
                                if mode != "empty":
                                    module_file(
                                        root, "Z", BAD if mode == "blocked" else GOOD
                                    )
                                    module_file(root, "A")
                                if mode in ("compile_failure", "launch_error"):
                                    (root / "compiler_mode").write_text(
                                        "failure" if mode == "compile_failure" else mode
                                    )
                                if mode == "output_error":
                                    (root / "report.json").mkdir()
                                if mode == "self_io_error":
                                    (
                                        root
                                        / "artifacts/mathformerphysicslib/foundations/verification_self_test.lean"
                                    ).mkdir(parents=True)
                                argv = flags + (
                                    ["--module", str(root / "missing.lean")]
                                    if mode == "missing"
                                    else []
                                )
                                argv += (
                                    ["--output", str(root / "report.json")]
                                    if output
                                    else []
                                )
                                argv += ["--json"] if print_json else []
                                stream = io.StringIO()
                                with (
                                    mount(module, root),
                                    patch.object(
                                        module.subprocess,
                                        "run",
                                        boundary.compiler_boundary,
                                    ),
                                    redirect_stdout(stream),
                                ):
                                    try:
                                        outcome = ("return", module.main(argv))
                                    except Exception as error:
                                        outcome = (
                                            "raise",
                                            type(error).__name__,
                                            str(error),
                                        )
                                outcomes.append(
                                    (outcome, stream.getvalue(), files(root))
                                )
                            self.assertEqual(outcomes[0], outcomes[1])
            # Duplicate explicit selections are retained, not deduplicated/sorted.
            clean(root)
            a = module_file(root, "A")
            b = module_file(root, "B", BAD)
            argv = [
                "--module",
                str(b),
                "--module",
                str(a),
                "--module",
                str(b),
                "--skip-index-compile",
            ]
            for module in (old, source):
                stream = io.StringIO()
                with mount(module, root), redirect_stdout(stream):
                    self.assertEqual(module.main(argv), 1)
                self.assertEqual(
                    [row["path"] for row in json.loads(stream.getvalue())["modules"]],
                    [str(LIB / f"{name}.lean") for name in ("B", "A", "B")],
                )
            for flags in (["--unknown"], ["--help"]):
                for module in (old, source):
                    with (
                        redirect_stdout(io.StringIO()),
                        redirect_stderr(io.StringIO()),
                        self.assertRaises(SystemExit) as caught,
                    ):
                        module.main(flags)
                    self.assertEqual(
                        caught.exception.code, 0 if flags == ["--help"] else 2
                    )

    def test_registered_tools_lunar_and_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_physics_lean_foundation_verify_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 264},
        )
        self.assertIn(
            SELECTED, [row["path"] for row in document["provenance"]["sources"]]
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        normalizer = load(
            "foundation_verify_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == document["id"]),
            document,
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "mount"
            root.mkdir()
            fixture(root)
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--serve", str(root)],
                cwd=str(ROOT),
            )
            env = {
                "LUNAR_PLATFORM_ROOT": str(LUNAR),
                "PYTHONPATH": str(FIXTURES / "foundation_verify_compiler"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            async with diagnosed_session(
                manager, "foundation-verify", config, env
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, advertised=tools):
                    assets = snapshot(doc)
                    return (
                        compile_workflow(
                            "mcp:foundation-verify",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            advertised,
                        ),
                        assets,
                    )

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(argv=(), allow=False, doc=document):
                    bound, received = (
                        (compiled, assets) if doc is document else compile(doc)
                    )
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    return await execute(
                        bound,
                        received,
                        {
                            "argv": list(argv),
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": allow,
                            },
                        },
                        remote,
                        authorize,
                    )

                def names(result):
                    return [
                        c.get("tool", "").removeprefix("mathformer_foundation_verify_")
                        for c in result["calls"]
                    ]

                async def completed(argv=(), allow=False, code=0, doc=document):
                    result = await run(argv, allow, doc)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["emission"]["exit_code"], code)
                    self.assertEqual(
                        json.loads(result["outputs"]["emission"]["text"]),
                        result["outputs"]["report"],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                # Empty selection still compiles; empty input never verifies successfully.
                result = await completed(allow=True, code=1)
                self.assertEqual(
                    names(result),
                    [
                        "parse",
                        "initialize",
                        "retain_empty",
                        "collect",
                        "compile_index",
                        "finalize",
                        "emit",
                    ],
                )
                self.assertEqual(result["outputs"]["report"]["module_count"], 0)
                self.assertEqual(result["outputs"]["report"]["blockers"], [])
                self.assertEqual(len(compiler_calls(root)), 1)
                clean(root)
                result = await completed(["--skip-index-compile"], code=1)
                self.assertEqual(
                    result["outputs"]["report"]["accepted_index_compile"],
                    {"ok": True, "skipped": True},
                )
                self.assertEqual(compiler_calls(root), [])
                # Source order and complete blocker flattening, followed by compilation.
                for mode in ("success", "failure"):
                    clean(root)
                    module_file(root, "Z", BAD)
                    module_file(root, "A")
                    (root / "compiler_mode").write_text(mode)
                    result = await completed(
                        ["--output", "reports/α.json", "--json"], True, 1
                    )
                    report = result["outputs"]["report"]
                    self.assertEqual(
                        names(result),
                        [
                            "parse",
                            "initialize",
                            "scan_next",
                            "scan_next",
                            "collect",
                            "compile_index",
                            "finalize",
                            "emit",
                        ],
                    )
                    self.assertEqual(
                        [m["path"] for m in report["modules"]],
                        [str(LIB / f"{n}.lean") for n in ("A", "Z")],
                    )
                    self.assertEqual(report["promotion_ready_count"], 1)
                    self.assertEqual(
                        report["modules"][0]["warnings"],
                        ["broad_mathlib_import_justified_for_foundation_bootstrap"],
                    )
                    self.assertEqual(
                        report["modules"][0]["declaration_comment_count"], 1
                    )
                    self.assertEqual(len(report["modules"][1]["blockers"]), 6)
                    self.assertEqual(
                        report["blockers"][:6],
                        [
                            str(LIB / "Z.lean") + ":" + b
                            for b in report["modules"][1]["blockers"]
                        ],
                    )
                    index = report["accepted_index_compile"]
                    self.assertEqual(index["stdout_tail"], "o" * 2000)
                    self.assertEqual(index["stderr_tail"], "e" * 2000)
                    self.assertEqual(index["returncode"], 7 if mode == "failure" else 0)
                    self.assertEqual(
                        len(report["blockers"]), 7 if mode == "failure" else 6
                    )
                    self.assertEqual(
                        json.loads((root / "reports/α.json").read_text()), report
                    )
                    self.assertTrue(
                        (root / "reports/α.json").read_text().endswith("\n")
                    )
                    self.assertEqual(len(compiler_calls(root)), 1)
                clean(root)
                a = module_file(root, "A")
                b = module_file(root, "B")
                result = await completed(
                    [
                        "--module",
                        str(b),
                        "--module",
                        str(a),
                        "--module",
                        str(b),
                        "--skip-index-compile",
                    ]
                )
                self.assertEqual(
                    [m["path"] for m in result["outputs"]["report"]["modules"]],
                    [str(LIB / f"{n}.lean") for n in ("B", "A", "B")],
                )
                # Public transition state contains every prior native result, with no input mutation.
                context = {"repository_root": str(root), "allow_mutating": False}
                args = source.parse_options(["--module", str(b), "--module", str(a)])
                state = (
                    await remote.call(
                        "mathformer_foundation_verify_initialize",
                        {"args": args, "context": context},
                    )
                )["state"]
                self.assertEqual(
                    state,
                    {
                        "scan": {"paths": [str(b), str(a)], "cursor": 0, "modules": []},
                        "done": False,
                        "self_test_report": None,
                    },
                )
                for cursor in range(2):
                    before = deepcopy(state)
                    advanced = await remote.call(
                        "mathformer_foundation_verify_scan_next",
                        {"state": state, "context": context},
                    )
                    self.assertEqual(state, before)
                    state = advanced["state"]
                    self.assertEqual(state["scan"]["cursor"], cursor + 1)
                    self.assertEqual(advanced["done"], cursor == 1)
                    self.assertEqual(
                        state["scan"]["modules"][:-1], before["scan"]["modules"]
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundation_verify_scan_next",
                        {"state": state, "context": context},
                    )
                # Self-test bypasses input selection and compiler, writes/checks/deletes one fixture.
                clean(root)
                result = await completed(
                    ["--self-test", "--module", "missing.lean"], True
                )
                self.assertEqual(
                    names(result),
                    ["parse", "self_test", "retain_empty", "self_test_report", "emit"],
                )
                self.assertEqual(result["outputs"]["report"]["module_count"], 1)
                self.assertFalse(
                    (
                        root
                        / "artifacts/mathformerphysicslib/foundations/verification_self_test.lean"
                    ).exists()
                )
                self.assertEqual(compiler_calls(root), [])
                # Done on the exact bound wins; defaults above the bound are rejected.
                clean(root)
                for n in range(256):
                    module_file(root, f"M{n:03}")
                result = await completed(["--skip-index-compile"])
                self.assertEqual(result["outputs"]["report"]["module_count"], 256)
                self.assertEqual(names(result).count("scan_next"), 256)
                module_file(root, "M256")
                failed = await run(["--skip-index-compile"])
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "initialize")
                self.assertEqual(
                    source.build_report(
                        sorted((root / LIB).glob("*.lean")),
                        compile_index=False,
                        repository_root=root,
                    )["module_count"],
                    257,
                )
                # Exhaustion retains visits but cannot collect, compile or emit a partial report.
                clean(root)
                module_file(root, "A")
                module_file(root, "B")
                reduced = deepcopy(document)
                reduced["flow"]["steps"][2]["max_iterations"] = 1
                failed = await run(["--output", "partial.json"], True, reduced)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(names(failed).count("scan_next"), 1)
                self.assertNotIn("collect", names(failed))
                self.assertFalse((root / "partial.json").exists())
                self.assertEqual(compiler_calls(root), [])
                # Actual argparse, file, launch and output errors propagate once, without retry.
                with self.assertRaises(ExecutionRejected):
                    await run(["x"] * 257, True)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundation_verify_parse", {"argv": ["x"] * 257}
                    )
                for argv, stop in (
                    (["--unknown"], "parse"),
                    (["--help"], "parse"),
                    (["--module", "missing.lean"], "scan_next"),
                ):
                    failed = await run(argv, True)
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(names(failed)[-1], stop)
                    self.assertEqual(names(failed).count(stop), 1)
                (root / "compiler_mode").write_text("launch_error")
                failed = await run(allow=True)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "compile_index")
                self.assertNotIn("finalize", names(failed))
                (root / "out.json").mkdir()
                failed = await run(
                    ["--skip-index-compile", "--output", "out.json"], True
                )
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "emit")
                # Authorization and symlink escape checks precede compiler/output effects.
                clean(root)
                module_file(root, "A")
                for argv, stop in (
                    ([], "compile_index"),
                    (["--self-test"], "self_test"),
                    (["--skip-index-compile", "--output", "out.json"], "emit"),
                ):
                    failed = await run(argv)
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(names(failed)[-1], stop)
                self.assertEqual(compiler_calls(root), [])
                self.assertFalse((root / "out.json").exists())
                outside = base / "outside"
                outside.mkdir()
                (root / "escape").symlink_to(outside, target_is_directory=True)
                for argv in (
                    ["--skip-index-compile", "--output", "escape/report.json"],
                    ["--module", "escape/missing.lean"],
                ):
                    failed = await run(argv, True)
                    self.assertEqual(failed["status"], "failed")
                self.assertEqual(files(outside), {})
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                failed = await run(doc=budget)
                self.assertEqual(failed["status"], "failed")
                self.assertIn("budget", failed["calls"][-1]["error"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    1,
                )
                # All failures leave the registered service usable.
                await completed(["--self-test"], True)
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        import mcp_server

        mcp_server.apply_runtime_config(allowed_write_roots=[sys.argv[2]])
        mcp_server.mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)
