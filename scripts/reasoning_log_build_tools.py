# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the registered reasoning-log builder and native hub audit."""

from contextlib import contextmanager, redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from threading import RLock
import traceback
from typing_extensions import TypedDict
import mathformer as hub
from scripts.workflow_write_audit import FileState

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/control/reasoning-log-schema-guardian/scripts/index_reasoning_logs.py"
LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "reasoning_log_builder_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def environment(context):
    """Resolve the real repository read/write context, restoring module constants."""
    root = Path(context["repository_root"]).resolve()
    if root != ROOT and not root.is_relative_to(ROOT / "artifacts/workflow_hub"):
        raise ValueError(
            "repository context must be the repository or a workflow_hub workspace"
        )
    with LOCK:
        native = source()
        modules = [
            hub,
            native,
            sys.modules["audit_reasoning_log_quality"],
            sys.modules["summarize_reasoning_log"],
        ]
        previous = [m.REPO_ROOT for m in modules]
        try:
            for module in modules:
                module.REPO_ROOT = root
            yield native, root
        finally:
            for module, old in zip(modules, previous):
                module.REPO_ROOT = old


class Prepared(TypedDict):
    boundary: dict
    result: dict


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    exhausted: bool


class Report(TypedDict):
    report: dict


class Result(TypedDict):
    result: dict


class Returned(TypedDict):
    result: dict
    state: dict


def register_reasoning_log_build_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_log_build_prepare(context: dict) -> Prepared:
        with environment(context):
            item = hub.build_registry()["control:reasoning-log-index"]
            options = {key: context[key] for key in hub.RunContext.__dataclass_fields__}
            boundary = hub.prepare_leaf_boundary(item, hub.RunContext(**options), [])
            # Preserve nanosecond integers through JSON/PRISM numeric codecs.
            boundary["snapshot"] = {
                path: {
                    "size": str(value.size),
                    "mtime_ns": str(value.mtime_ns),
                    "digest": value.digest,
                }
                for path, value in boundary["snapshot"].items()
            }
            boundary["context"] = context
            return {"boundary": boundary, "result": boundary["payload"]}

    @mcp.tool()
    def mathformer_log_build_return(boundary: dict) -> Returned:
        return {
            "result": boundary["payload"],
            "state": {
                "logs": [],
                "position": 0,
                "entries": [],
                "hooks_file": "",
                "output_file": "",
                "summary_dir": "",
                "context": boundary["context"],
                "terminal": True,
            },
        }

    @mcp.tool()
    def mathformer_log_build_initialize(logs: list[str], boundary: dict) -> State:
        if not boundary["execute"] or logs != [
            "artifacts/reasoning/self_test/good.jsonl"
        ]:
            raise ValueError(
                "requires executable boundary and registered log selection"
            )
        write_policy()
        context = boundary["context"]
        with environment(context) as (native, root):
            try:
                native.write_self_test_fixtures()
                state = native.initialize_index(
                    log_files=[root / p for p in logs],
                    hooks_file=root / "skills/SKILL_HOOKS.yaml",
                    output_file=root / "artifacts/reasoning/index.json",
                )
            except Exception:
                state = {
                    "logs": logs,
                    "position": 0,
                    "entries": [],
                    "hooks_file": "",
                    "output_file": "",
                    "summary_dir": "",
                    "error": traceback.format_exc(),
                }
            state["context"] = context
            return {"state": state}

    @mcp.tool()
    def mathformer_log_build_next(state: dict) -> Advanced:
        if state.get("terminal"):
            return {"state": state, "exhausted": True}
        write_policy()
        with environment(state["context"]) as (native, root):
            if not state.get("error"):
                # State travels as data: never accept paths outside this repository.
                for path in [
                    *state["logs"],
                    state["output_file"],
                    state["summary_dir"],
                ]:
                    Path(path).resolve().relative_to(root / "artifacts/reasoning")
                Path(state["hooks_file"]).resolve().relative_to(root / "skills")
                try:
                    native.index_next_log(state)
                except Exception:
                    state["error"] = traceback.format_exc()
            return {
                "state": state,
                "exhausted": bool(state.get("error"))
                or state["position"] >= len(state["logs"]),
            }

    @mcp.tool()
    def mathformer_log_build_write(state: dict) -> Report:
        write_policy()
        with environment(state["context"]) as (native, root):
            if state.get("error"):
                return {"report": {"error": state["error"]}}
            Path(state["output_file"]).resolve().relative_to(
                root / "artifacts/reasoning"
            )
            try:
                return {"report": native.write_index(state)}
            except Exception:
                return {"report": {"error": traceback.format_exc()}}

    @mcp.tool()
    def mathformer_log_build_finish(boundary: dict, report: dict) -> Result:
        with environment(boundary["context"]) as (native, _):
            payload = dict(boundary["payload"])
            stream = io.StringIO()
            if "error" in report:
                code, stderr = 1, report["error"]
            else:
                with redirect_stdout(stream):
                    code = native.emit_report(report, json_output=True)
                stderr = ""
            payload.update(
                status="completed",
                returncode=code,
                stdout=stream.getvalue(),
                stderr=stderr,
                ok=code == 0,
            )
            print(payload["stdout"], end="", file=sys.stderr)
            print(stderr, end="", file=sys.stderr)
            item = hub.build_registry()["control:reasoning-log-index"]
            restored = {
                **boundary,
                "snapshot": {
                    path: FileState(
                        size=int(value["size"]),
                        mtime_ns=int(value["mtime_ns"]),
                        digest=value["digest"],
                    )
                    for path, value in boundary["snapshot"].items()
                },
            }
            return {"result": hub.finish_leaf_boundary(item, restored, payload)}
