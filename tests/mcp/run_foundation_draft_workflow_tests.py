#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real source, MCP registration, Lunar compiler and PRISM runtime fixtures.

The native workflow has no provider/model or external compiler boundary. These
fixtures substitute none of its steps and run no Lean/theorem-prover process.
Only the legacy entrypoint's fixed filesystem constants are mounted on temp dirs.
WORKFLOW_CONTRACT_PATH explicitly selects the candidate or installed descriptor.
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
    contextmanager,
    asynccontextmanager,
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
import yaml
from foundation_draft_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_foundation_draft_workflow/workflow.yaml"
LIB = Path("MathformerPhysicsLib/Lean")


def oracle():
    name = "foundation_draft_oracle"
    loader = SourceFileLoader(
        name, str(ROOT / "tests/mcp/fixtures/foundation_draft_original.py.txt")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def mount(module, root):
    values = dict(
        REPO_ROOT=root,
        FOUNDATION_ROOT=root / LIB / "Foundations",
        INDEX_PATH=root / LIB / "Foundations.lean",
    )
    before = {key: getattr(module, key) for key in values}
    for key, value in values.items():
        setattr(module, key, value)
    try:
        yield
    finally:
        for key, value in before.items():
            setattr(module, key, value)


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def clean(root):
    for path in root.iterdir():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
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


class FoundationTests(unittest.TestCase):
    def test_native_entrypoint_equivalence(self):
        old = oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plans = [
                {},
                {
                    "source_packet_id": "Unicode α",
                    "surfaces": [
                        None,
                        3,
                        {"foundation_module": "Units"},
                        {"foundation_module": "Fields"},
                        {"foundation_module": "Fields"},
                        {"foundation_module": "unknown"},
                    ],
                },
                {"surfaces": [{"foundation_module": "unknown"}]},
                [],
                {"surfaces": None},
            ]
            for plan in plans:
                for write in (False, True):
                    for self_test in (False, True):
                        for output, print_json in (
                            (False, False),
                            (True, False),
                            (True, True),
                        ):
                            with self.subTest(
                                plan=plan,
                                write=write,
                                self_test=self_test,
                                output=output,
                                json=print_json,
                            ):
                                outcomes = []
                                for module in (old, source):
                                    clean(root)
                                    plan_path = root / "plan.json"
                                    plan_path.write_text(json.dumps(plan))
                                    argv = (
                                        ["--surface-plan", str(plan_path)]
                                        + (["--write"] if write else [])
                                        + (["--self-test"] if self_test else [])
                                        + (
                                            [
                                                "--output",
                                                str(root / "nested/report.json"),
                                            ]
                                            if output
                                            else []
                                        )
                                        + (["--json"] if print_json else [])
                                    )
                                    stream = io.StringIO()
                                    with mount(module, root), redirect_stdout(stream):
                                        try:
                                            outcome = ("return", module.main(argv))
                                        except Exception as error:
                                            outcome = ("raise", type(error).__name__)
                                    outcomes.append(
                                        (outcome, stream.getvalue(), files(root))
                                    )
                                self.assertEqual(outcomes[0], outcomes[1])
                                if self_test:
                                    self.assertFalse((root / LIB).exists())
                                elif (
                                    write
                                    and isinstance(plan, dict)
                                    and plan.get("surfaces") is not None
                                ):
                                    self.assertEqual(
                                        (root / LIB / "Foundations.lean").read_text(),
                                        old.INDEX_TEXT,
                                    )
            # Exact failures and partial writes are preserved; no rollback/retry.
            for mode in (
                "bad_json",
                "missing",
                "module_failure",
                "index_failure",
                "output_failure",
            ):
                outcomes = []
                for module in (old, source):
                    clean(root)
                    plan = root / "plan.json"
                    plan.write_text("{" if mode == "bad_json" else "{}")
                    if mode == "missing":
                        plan.unlink()
                    if mode == "module_failure":
                        (root / LIB / "Foundations/Contexts.lean").mkdir(parents=True)
                    if mode == "index_failure":
                        (root / LIB / "Foundations.lean").mkdir(parents=True)
                    if mode == "output_failure":
                        (root / "report.json").mkdir()
                    stream = io.StringIO()
                    with mount(module, root), redirect_stdout(stream):
                        try:
                            outcome = (
                                "return",
                                module.main(
                                    [
                                        "--write",
                                        "--surface-plan",
                                        str(plan),
                                        "--output",
                                        str(root / "report.json"),
                                    ]
                                ),
                            )
                        except Exception as error:
                            outcome = ("raise", type(error).__name__)
                    outcomes.append((outcome, stream.getvalue(), files(root)))
                self.assertEqual(outcomes[0], outcomes[1])
                self.assertEqual(outcomes[1][0][0], "raise")
            for argv in (["--unknown"], ["--help"]):
                exits = []
                for module in (old, source):
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as caught:
                            module.main(argv)
                    exits.append(caught.exception.code)
                self.assertEqual(exits, [0, 0] if argv == ["--help"] else [2, 2])
            clean(root)
            for plan in plans[:3]:
                with mount(old, root), mount(source, root):
                    self.assertEqual(
                        old.build_draft(plan, write=False),
                        source.build_draft(plan, write=False),
                    )

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_physics_lean_foundation_draft_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 15},
        )
        self.assertIn(
            str(source.__file__).removeprefix(str(ROOT) + "/"),
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "foundation_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == document["id"]),
            document,
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "mount"
            root.mkdir()
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--serve", str(root)],
                cwd=str(ROOT),
            )
            async with diagnosed_session(
                manager, "foundation", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, advertised=tools):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:foundation",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        advertised,
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(argv=(), allow=False, doc=document):
                    selected, received = (
                        (compiled, assets) if doc is document else compile(doc)
                    )
                    self.assertTrue(selected["runnable"], selected["diagnostics"])
                    return await execute(
                        selected,
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
                        c.get("tool", "").removeprefix("mathformer_foundation_draft_")
                        for c in result["calls"]
                    ]

                async def success(argv=(), allow=False, doc=document):
                    result = await run(argv, allow, doc)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                # Empty/default and unrecognized plans traverse all ten modules.
                result = await success()
                self.assertEqual(
                    names(result),
                    [
                        "parse",
                        "load_request",
                        "initialize",
                        *(["draft_next"] * 10),
                        "finish",
                        "emit",
                    ],
                )
                self.assertEqual(
                    [item["module"] for item in result["outputs"]["report"]["modules"]],
                    sorted(source.TEMPLATES),
                )
                self.assertEqual(files(root), {})
                self.assertEqual(
                    result["outputs"]["report"]["terminal_state"], "draft_preview"
                )
                for plan in (
                    {"surfaces": [{"foundation_module": "unknown"}]},
                    {
                        "source_packet_id": "α",
                        "surfaces": [
                            False,
                            {"foundation_module": "Units"},
                            {"foundation_module": "Fields"},
                            {"foundation_module": "Fields"},
                            {"foundation_module": None},
                        ],
                    },
                ):
                    for write in (False, True):
                        clean(root)
                        (root / "plan.json").write_text(json.dumps(plan))
                        argv = [
                            "--surface-plan",
                            "plan.json",
                            "--output",
                            "reports/draft.json",
                        ] + (["--write"] if write else [])
                        before = files(root)
                        # Original CLI uses absolute flags; root is its mounted cwd.
                        original_argv = [
                            "--surface-plan",
                            str(root / "plan.json"),
                            "--output",
                            str(root / "reports/draft.json"),
                        ] + (["--write"] if write else [])
                        with (
                            mount(oracle_module := oracle(), root),
                            redirect_stdout(io.StringIO()),
                        ):
                            oracle_module.main(original_argv)
                        expected = files(root)
                        clean(root)
                        for name, data in before.items():
                            p = root / name
                            p.parent.mkdir(parents=True, exist_ok=True)
                            p.write_bytes(data)
                        result = await success(argv, True)
                        self.assertEqual(files(root), expected)
                        report = result["outputs"]["report"]
                        self.assertEqual(
                            json.loads((root / "reports/draft.json").read_text()),
                            report,
                        )
                        self.assertEqual(
                            report["source_surface_plan"], plan.get("source_packet_id")
                        )
                        self.assertEqual(report["write"], write)
                        if write:
                            self.assertEqual(
                                (root / LIB / "Foundations.lean").read_text(),
                                source.INDEX_TEXT,
                            )
                            for item in report["modules"]:
                                self.assertEqual(
                                    (root / item["path"]).read_text(),
                                    source.TEMPLATES[item["module"]],
                                )
                                self.assertEqual(
                                    item["declaration_count"],
                                    source.TEMPLATES[item["module"]].count("/--"),
                                )
                                self.assertEqual(item["state"], "candidate_generated")
                # The self-test ignores both a missing input and --write, and stops after Fields.
                clean(root)
                result = await success(
                    ["--self-test", "--write", "--surface-plan", "missing.json"]
                )
                self.assertEqual(
                    names(result),
                    [
                        "parse",
                        "self_test_request",
                        "initialize",
                        "draft_next",
                        "finish",
                        "emit",
                    ],
                )
                self.assertEqual(
                    result["outputs"]["report"]["modules"][0]["module"], "Fields"
                )
                self.assertEqual(
                    result["outputs"]["report"]["source_surface_plan"], "self_test"
                )
                self.assertEqual(files(root), {})
                # Inspect actual iterator state, including history, through public tools.
                request = {
                    "plan": {
                        "surfaces": [
                            {"foundation_module": "Fields"},
                            {"foundation_module": "Units"},
                        ]
                    },
                    "write": False,
                }
                state = (
                    await remote.call(
                        "mathformer_foundation_draft_initialize", {"request": request}
                    )
                )["state"]
                self.assertEqual(
                    state,
                    {
                        "modules": ["Fields", "Units"],
                        "cursor": 0,
                        "items": [],
                        "item_history": [],
                    },
                )
                initial = deepcopy(state)
                for i in range(2):
                    advanced = await remote.call(
                        "mathformer_foundation_draft_draft_next",
                        {
                            "request": request,
                            "state": state,
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": False,
                            },
                        },
                    )
                    state = advanced["state"]
                    self.assertEqual(advanced["done"], i == 1)
                    self.assertEqual(state["cursor"], i + 1)
                    self.assertEqual(
                        state["items"], [json.loads(s) for s in state["item_history"]]
                    )
                    self.assertEqual(len(state["items"]), i + 1)
                self.assertEqual(initial["items"], [])
                # Exact full bound succeeds; one fewer visit fails before index/report emission.
                await success()
                reduced = deepcopy(document)
                reduced["flow"]["steps"][3]["max_iterations"] = 9
                failed = await run(["--write"], True, reduced)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["failure_disposition"], "fail")
                self.assertEqual(names(failed).count("draft_next"), 9)
                self.assertNotIn("finish", names(failed))
                self.assertEqual(
                    len(list((root / LIB / "Foundations").glob("*.lean"))), 9
                )
                self.assertFalse((root / LIB / "Foundations.lean").exists())
                # Native parse, file/JSON and malformed plan failures stop their dependent steps.
                for mode, argv, stop in (
                    ("bad_flag", ["--unknown"], "parse"),
                    ("help", ["--help"], "parse"),
                    ("missing", ["--surface-plan", "missing.json"], "load_request"),
                    ("bad_json", ["--surface-plan", "bad.json"], "load_request"),
                    ("bad_plan", ["--surface-plan", "bad.json"], "initialize"),
                ):
                    clean(root)
                    (root / "bad.json").write_text("[]" if mode == "bad_plan" else "{")
                    failed = await run(argv)
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(names(failed)[-1], stop)
                    self.assertEqual(names(failed).count(stop), 1)
                # A failed middle write retains earlier modules, with no finish or report.
                clean(root)
                (root / LIB / "Foundations/Contexts.lean").mkdir(parents=True)
                failed = await run(["--write", "--output", "out.json"], True)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed).count("draft_next"), 2)
                self.assertEqual(
                    (root / LIB / "Foundations/Carriers.lean").read_text(),
                    source.TEMPLATES["Carriers"],
                )
                self.assertFalse((root / "out.json").exists())
                self.assertNotIn("finish", names(failed))
                for mode, stop in (("index", "finish"), ("output", "emit")):
                    clean(root)
                    (
                        root
                        / (
                            LIB / "Foundations.lean"
                            if mode == "index"
                            else Path("out.json")
                        )
                    ).mkdir(parents=True)
                    failed = await run(["--write", "--output", "out.json"], True)
                    self.assertEqual(failed["status"], "failed")
                    self.assertEqual(names(failed)[-1], stop)
                    self.assertEqual(
                        len(list((root / LIB / "Foundations").glob("*.lean"))), 10
                    )
                # Source self-test assertions remain real and propagate through registration.
                clean(root)
                opts = source.parse_options(["--self-test"])
                req = {
                    "plan": {"surfaces": [{"foundation_module": "Units"}]},
                    "write": False,
                }
                state = source.initialize_draft(req)
                state = source.draft_next(req, state, root)["state"]
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundation_draft_finish",
                        {
                            "request": req,
                            "state": state,
                            "options": opts,
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": False,
                            },
                        },
                    )
                # Authorization and call budgets fail closed without touching other mounts.
                clean(root)
                failed = await run(["--write"])
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "draft_next")
                self.assertEqual(files(root), {})
                failed = await run(["--output", "out.json"])
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed)[-1], "emit")
                self.assertEqual(files(root), {})
                outside = base / "outside"
                outside.mkdir()
                failed = await run(["--output", str(outside / "out.json")], True)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(files(outside), {})
                (root / "MathformerPhysicsLib").symlink_to(
                    outside, target_is_directory=True
                )
                failed = await run(["--write"], True)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(files(outside), {})
                clean(root)
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
                self.assertEqual(files(root), {})
                # Rejected argparse requests do not kill the real MCP transport.
                await success(["--self-test"])
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        import mcp_server

        mcp_server.apply_runtime_config(allowed_write_roots=[sys.argv[2]])
        mcp_server.mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)
