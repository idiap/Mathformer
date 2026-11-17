#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run native chapter steps, registered MCP tools and Lunar PRISM with fixtures."""

from tempfile import gettempdir

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"]).resolve()
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
from copy import deepcopy
import hashlib
import json
import subprocess
import tempfile
import unittest
import yaml
from textbook_chapter_boundary import prepare, SOURCE
from textbook_chapter_workflow_tools import (
    AUTHORED,
    register_textbook_chapter_tools,
    chapter_source,
    native_options,
)
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"]).resolve()
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_textbook_theory_autoformalization_loop_workflow/workflow.yaml"


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


def stable(value, root):
    if isinstance(value, dict):
        return {
            k: stable(v, root)
            for k, v in value.items()
            if k
            not in {
                "created_at",
                "updated_at",
                "started_at",
                "completed_at",
                "generated_at_utc",
                "created_at_utc",
                "duration_ms",
                "timestamp_utc",
                "timestamp",
            }
        }
    if isinstance(value, list):
        return [stable(v, root) for v in value]
    if isinstance(value, str):
        try:
            return stable(json.loads(value), root)
        except (ValueError, TypeError):
            return (
                value.replace(str(root), "<ROOT>")
                .replace("oracle_out", "OUT")
                .replace("lunar_out", "OUT")
            )
    return value


def read(path):
    return json.loads(Path(path).read_text())


def ledger(root):
    path = root / "processes.jsonl"
    return (
        [json.loads(t) for t in path.read_text().splitlines()] if path.exists() else []
    )


def report():
    units = []
    for i, title in enumerate(["Foundations", "Applications"], 1):
        for j, kind in enumerate(["theorem", "proof", "definition"], 1):
            uid = f"u{i}-{j}"
            units.append(
                dict(
                    id=uid,
                    kind=kind,
                    env=kind,
                    title=f"{title} {kind}",
                    file=f"chapter{i}.tex",
                    chapter=title,
                    section="Objects",
                    line_start=j,
                    line_end=j,
                    latex=f"A source {kind}.",
                    body=f"A source {kind}.",
                    source_order=len(units) + 1,
                    labels=[],
                    references=[],
                    citations=[],
                    paired_proof_unit_ids=[f"u{i}-2"] if j == 1 else [],
                    proof_for_unit_id=f"u{i}-1" if j == 2 else None,
                )
            )
    return dict(schema_version=1, source_root=None, archive=None, units=units)


class TextbookTests(unittest.TestCase):
    def test_contract_and_native_guards(self):
        self.assertEqual(DOCUMENT, read(AUTHORED))
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertIn(SOURCE, [s["path"] for s in DOCUMENT["provenance"]["sources"]])
        for source in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        # The generator must select the authored contract without publishing it.
        import importlib.util

        generator_path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "textbook_normalizer", generator_path
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.textbook_chapter_descriptor(), DOCUMENT)
        native = chapter_source()
        args = native_options(native, {})
        # Delegated kind filtering precedes offset and max slicing. The chapter
        # caller intentionally supplies no kind selector.
        runner_spec = importlib.util.spec_from_file_location(
            "textbook_runner", native.RUN_BATCH_SCRIPT
        )
        runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(runner)
        jobs = dict(
            jobs=[
                dict(job_id="a", target_kind="proof"),
                dict(job_id="b", target_kind="theorem"),
                dict(job_id="c", target_kind="proof"),
            ]
        )
        self.assertEqual(
            runner.select_jobs(jobs, start_at=2, max_jobs=1, kind="proof"),
            [jobs["jobs"][2]],
        )
        self.assertEqual(
            runner.select_jobs(jobs, start_at=1, max_jobs=0, kind=None), []
        )

        self.assertEqual(
            (args.provider, args.timeout_sec, args.run_timeout_sec), ("none", 600, 1800)
        )
        with self.assertRaisesRegex(ValueError, "no chapter"):
            native.inventory_and_pack(
                native_options(native, {"chapter_id": "absent"}), report()
            )
        self.assertEqual(
            native.inventory_and_pack(
                native_options(native, {"max_chapters": 0}), report()
            )["remaining"],
            [],
        )
        # Native cross-chapter pairing closure must preserve source-linked units.
        theory = report()
        theory["units"][0]["paired_proof_unit_ids"].append("u2-2")
        selected = native.chapter_inventory(theory["units"])[0]
        self.assertIn("u2-2", [u["id"] for u in native.chapter_units(theory, selected)])
        from mcp.server.fastmcp import FastMCP

        async def denied():
            server = FastMCP("denied")

            def reject():
                raise PermissionError("read-only service")

            register_textbook_chapter_tools(server, reject)
            state = native.inventory_and_pack(args, report())
            state["has_chapters"] = True
            with self.assertRaisesRegex(Exception, "read-only service"):
                await server.call_tool(
                    "mathformer_textbook_chapter_prepare",
                    dict(
                        state=state,
                        options={},
                        full_report=report(),
                        output_dir=str(
                            Path(gettempdir()) / "mathformer-test-fixtures/unused"
                        ),
                    ),
                )
            server = FastMCP("outside")
            register_textbook_chapter_tools(server, path_allowed=lambda p: False)
            with self.assertRaisesRegex(Exception, "write roots"):
                await server.call_tool(
                    "mathformer_textbook_chapter_write",
                    dict(
                        state=state,
                        options={},
                        theory_path=str(
                            Path(gettempdir()) / "mathformer-test-fixtures/unused"
                        ),
                        output_dir=str(
                            Path(gettempdir()) / "mathformer-test-fixtures/unused"
                        ),
                    ),
                )

        asyncio.run(denied())

    def test_registered_tools_lunar_runtime_and_original_parity(self):
        asyncio.run(self.scenarios())

    async def scenarios(self):
        with tempfile.TemporaryDirectory(prefix="textbook-binding-") as tmp:
            root = prepare(Path(tmp) / "repo", ROOT)
            driver = root / "oracle_driver.py"
            driver.write_text(
                """import json,sys,types,importlib.util
from pathlib import Path
root=Path(__file__).parent
source=root/"""
                + repr(SOURCE)
                + """
spec=importlib.util.spec_from_file_location('current',source)
current=importlib.util.module_from_spec(spec);spec.loader.exec_module(current)
original=types.ModuleType('original');original.__file__=str(source)
exec(compile((root/'original.py.txt').read_text(),str(source),'exec'),original.__dict__)
values=json.loads((root/'inputs.json').read_text())
args=current.parse_args([])
for k,v in values['options'].items():
    setattr(args,k,Path(v) if k in {'archive','source_dir'} and v is not None else v)
result=original.build_chapter_plan(args=args,output_dir=Path(values['output_dir']),theory_path=Path(values['theory_path']),full_report=values['full_report'])
(root/'oracle-result.json').write_text(json.dumps(result))
"""
            )
            (root / "original.py.txt").write_text(
                (
                    ROOT / "tests/mcp/fixtures/textbook_chapter_original.py.txt"
                ).read_text()
            )
            paths = [
                str(ROOT / "tests/mcp/fixtures/textbook_boundaries"),
                str(ROOT / "tests/mcp/fixtures"),
                str(ROOT / "scripts"),
                *[str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")],
            ]
            env = {
                "PYTHONPATH": os.pathsep.join(paths),
                "TEXTBOOK_FIXTURE_ROOT": str(root),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PATH": str(LUNAR / ".venv/bin") + os.pathsep + os.environ["PATH"],
            }
            manager = SessionManager()
            code = "from textbook_chapter_boundary import serve; import sys; serve(sys.argv[1])"
            failure = None
            async with manager.open(
                "textbook-fixture",
                StdioConfig(
                    command=sys.executable, args=["-c", code, str(root)], cwd=str(ROOT)
                ),
                env,
            ) as remote:
                try:
                    advertised = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_document(document):
                        snapshot = assets(document)
                        workflows = workflow_documents([DESCRIPTOR], snapshot)
                        self.assertEqual(len(workflows), 1)
                        compiled = compile_workflow(
                            "mcp:textbook-fixture", workflows[0], advertised
                        )
                        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                        self.assertEqual(
                            set(compiled["bindings"]), set(document["operations"])
                        )
                        self.assertTrue(compiled["runtime_source"])
                        return compiled, snapshot

                    compiled, snapshot = compile_document(DOCUMENT)

                    async def allow():
                        pass

                    cases = [
                        ("queue", {}, report()),
                        ("empty", {}, dict(units=[])),
                        ("zero", {"max_chapters": 0}, report()),
                        (
                            "filter",
                            {
                                "chapter_id": "APPLICATIONS",
                                "max_chapters": 1,
                                "no_proof_jobs": True,
                            },
                            report(),
                        ),
                        ("missing", {"chapter_index": 3}, report()),
                        (
                            "malformed",
                            {},
                            dict(units=[dict(kind="theorem", chapter="Broken")]),
                        ),
                        ("none", {"run_chapter_index": 1}, report()),
                        (
                            "unavailable",
                            {"run_chapter_index": 1, "provider": "codex-cli"},
                            report(),
                        ),
                        (
                            "good",
                            {
                                "run_chapter_id": "FOUND",
                                "provider": "codex-cli",
                                "max_jobs_per_chapter": 2,
                                "max_run_jobs": 1,
                                "start_at": 2,
                            },
                            report(),
                        ),
                        (
                            "mixed",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 2,
                            },
                            report(),
                        ),
                        (
                            "outer_timeout",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                                "run_timeout_sec": 1,
                            },
                            report(),
                        ),
                        (
                            "compiler_fail",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "realness_fail",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "timeout",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 2,
                            },
                            report(),
                        ),
                        (
                            "blocked",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "empty_generation",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "provider_fail",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "provider_crash",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "compiler_timeout",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        (
                            "skip",
                            {
                                "run_chapter_index": 1,
                                "provider": "codex-cli",
                                "skip_lean_check": True,
                                "max_run_jobs": 1,
                            },
                            report(),
                        ),
                        ("offset", {"run_chapter_index": 1, "start_at": 99}, report()),
                    ]
                    for name, options, theory in cases:
                        with self.subTest(case=name):
                            for dirname in ["oracle_out", "lunar_out"]:
                                import shutil

                                shutil.rmtree(root / dirname, ignore_errors=True)
                            mode = "empty" if name == "empty_generation" else name
                            (root / "case.json").write_text(json.dumps(dict(mode=mode)))
                            inputs = dict(
                                options=options,
                                full_report=theory,
                                theory_path=str(root / "theory.json"),
                                output_dir=str(root / "oracle_out"),
                            )
                            (root / "theory.json").write_text(json.dumps(theory))
                            (root / "inputs.json").write_text(json.dumps(inputs))
                            before = len(ledger(root))
                            original = subprocess.run(
                                [sys.executable, str(driver)],
                                cwd=root,
                                env={**os.environ, **env},
                                capture_output=True,
                                text=True,
                                timeout=120,
                            )
                            expected_calls = ledger(root)[before:]
                            inputs["output_dir"] = str(root / "lunar_out")
                            before = len(ledger(root))
                            result = await execute(
                                compiled, snapshot, inputs, remote, allow
                            )
                            actual_calls = ledger(root)[before:]
                            self.assertEqual(
                                stable(actual_calls, root), stable(expected_calls, root)
                            )
                            if original.returncode:
                                self.assertEqual(result["status"], "failed", result)
                                self.assertIsNone(result["outputs"])
                                self.assertFalse(
                                    (root / "lunar_out/chapter_plan.json").exists()
                                )
                                self.assertEqual(
                                    result["calls"][-1]["status"], "rejected"
                                )
                                self.assertEqual(
                                    result["calls"][-1]["operation"],
                                    (
                                        "inventory_and_pack"
                                        if name == "missing"
                                        else (
                                            "prepare_chapter"
                                            if name == "malformed"
                                            else "run_objects"
                                        )
                                    ),
                                )
                                continue
                            self.assertEqual(result["status"], "accepted", result)
                            plan = result["outputs"]["chapter_plan"]
                            self.assertEqual(
                                stable(plan, root),
                                stable(read(root / "oracle-result.json"), root),
                            )
                            self.assertEqual(
                                plan, read(root / "lunar_out/chapter_plan.json")
                            )
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            self.assertEqual(
                                len(plan["chapters"]),
                                (
                                    0
                                    if name in {"empty", "zero"}
                                    else 1 if name == "filter" else 2
                                ),
                            )
                            if name in {"queue", "filter"}:
                                self.assertFalse(
                                    any(
                                        "run_textbook_autoformalization_batch.py"
                                        in c["cmd"][1]
                                        for c in actual_calls
                                    )
                                )
                            for chapter in plan["chapters"]:
                                inventory = read(chapter["theory_units_json"])
                                self.assertTrue(inventory["units"])
                                self.assertTrue(
                                    Path(chapter["organized_manifest"]).is_file()
                                )
                                batch = read(chapter["batch_manifest"])
                                self.assertTrue(batch["jobs"])
                                if chapter["run_manifest"]:
                                    run = read(chapter["run_manifest"])
                                    self.assertEqual(
                                        run["selected_job_count"],
                                        (
                                            0
                                            if name == "offset"
                                            else min(
                                                len(batch["jobs"]),
                                                options.get(
                                                    "max_run_jobs", len(batch["jobs"])
                                                ),
                                            )
                                        ),
                                    )
                                    statuses = run["summary"]["status_counts"]
                                    expected = {
                                        "none": "blocked_no_generative_provider",
                                        "unavailable": "blocked_no_generative_provider",
                                        "good": "complete",
                                        "compiler_fail": "complete",
                                        "realness_fail": "draft_failed_gates",
                                        "timeout": "blocked_generation",
                                        "blocked": "blocked_generation",
                                        "empty_generation": "blocked_generation",
                                        "provider_fail": "blocked_generation",
                                        "compiler_timeout": "draft_failed_gates",
                                        "skip": "complete",
                                    }
                                    if name == "mixed":
                                        self.assertEqual(
                                            statuses,
                                            {"blocked_generation": 1, "complete": 1},
                                        )
                                    if name in expected:
                                        self.assertEqual(
                                            set(statuses), {expected[name]}
                                        )
                                    for job in run["results"]:
                                        persisted = read(job["result_file"])
                                        self.assertEqual(
                                            job["status"], persisted["status"]
                                        )
                                        if persisted["gates"]:
                                            self.assertTrue(
                                                Path(
                                                    persisted["gates"]["realness"][
                                                        "report_file"
                                                    ]
                                                ).exists()
                                            )
                                        if name == "compiler_fail":
                                            consistency = read(
                                                persisted["gates"]["consistency"][
                                                    "report_file"
                                                ]
                                            )
                                            self.assertFalse(consistency["ok"])
                                            self.assertIn(
                                                "lean_compile",
                                                consistency["blocking_layers"],
                                            )
                                    if name == "good":
                                        self.assertEqual(
                                            run["results"][0]["job_id"],
                                            batch["jobs"][1]["job_id"],
                                        )
                                    if name == "offset":
                                        self.assertEqual(run["results"], [])
                            if name == "none":
                                (root / "case.json").write_text('{"mode":"good"}')
                                for force in [False, True]:
                                    resumed = {
                                        **inputs,
                                        "options": dict(
                                            run_chapter_index=1,
                                            provider="codex-cli",
                                            max_run_jobs=1,
                                            force=force,
                                        ),
                                    }
                                    resumed["output_dir"] = str(root / "oracle_out")
                                    (root / "inputs.json").write_text(
                                        json.dumps(resumed)
                                    )
                                    original_again = subprocess.run(
                                        [sys.executable, str(driver)],
                                        cwd=root,
                                        env={**os.environ, **env},
                                        capture_output=True,
                                        text=True,
                                        timeout=120,
                                    )
                                    self.assertEqual(
                                        original_again.returncode,
                                        0,
                                        original_again.stderr,
                                    )
                                    resumed["output_dir"] = str(root / "lunar_out")
                                    before = len(ledger(root))
                                    replay = await execute(
                                        compiled, snapshot, resumed, remote, allow
                                    )
                                    self.assertEqual(
                                        replay["status"], "accepted", replay
                                    )
                                    self.assertEqual(
                                        stable(replay["outputs"]["chapter_plan"], root),
                                        stable(read(root / "oracle-result.json"), root),
                                    )
                                    calls = ledger(root)[before:]
                                    self.assertEqual(
                                        sum(c["cmd"][0] == "codex" for c in calls),
                                        int(force),
                                    )
                                    manifest = read(
                                        replay["outputs"]["chapter_plan"]["chapters"][
                                            0
                                        ]["run_manifest"]
                                    )
                                    self.assertEqual(manifest["selected_job_count"], 1)
                                    self.assertEqual(manifest["processed_job_count"], 3)
                                    self.assertEqual(
                                        manifest["summary"]["status_counts"],
                                        (
                                            {
                                                "blocked_no_generative_provider": 2,
                                                "complete": 1,
                                            }
                                            if force
                                            else {"blocked_no_generative_provider": 3}
                                        ),
                                    )
                            if name == "skip":
                                self.assertFalse(
                                    any(c["cmd"][0] == "lake" for c in actual_calls)
                                )
                    # Exhaustion sentinel: a smaller host bound fails after one
                    # chapter and never writes a final plan; the native max bound
                    # finishes normally at its selected last chapter.
                    (root / "case.json").write_text('{"mode":"good"}')
                    cut = deepcopy(DOCUMENT)
                    cut["flow"]["steps"][1]["max_iterations"] = 1
                    bounded, snap = compile_document(cut)
                    inputs = dict(
                        options={},
                        full_report=report(),
                        theory_path=str(root / "theory.json"),
                        output_dir=str(root / "bounded"),
                    )
                    failed = await execute(bounded, snap, inputs, remote, allow)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertFalse((root / "bounded/chapter_plan.json").exists())
                    inputs["options"] = {"max_chapters": 1}
                    accepted = await execute(bounded, snap, inputs, remote, allow)
                    self.assertEqual(accepted["status"], "accepted", accepted)
                    self.assertEqual(
                        len(accepted["outputs"]["chapter_plan"]["chapters"]), 1
                    )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
