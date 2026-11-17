# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP continuations for run_generative.main, sharing its actual source steps.

This models main, not the surrounding hub controller. The authored projection
admits at most 10000 probes; the original CLI has no such restriction.
"""

from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import importlib.util
import io
from pathlib import Path
import threading
from uuid import uuid4
from typing_extensions import TypedDict


def source_runner():
    path = Path(__file__).resolve().parents[1] / "tests/run_generative.py"
    spec = importlib.util.spec_from_file_location("_generative_probe_runner", path)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


class Initialized(TypedDict):
    state: dict
    runtime: dict


class Inspected(TypedDict):
    state: dict


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    completion: dict


def register_generative_probe_workflow_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    native = source_runner()
    sessions = {}
    lock = threading.RLock()

    def scope_for(runtime, phase, payload):
        scope = sessions.get(runtime.get("handle"))
        if not scope or runtime != {"handle": scope["handle"]}:
            raise ValueError("unknown runtime handle")
        if scope["phase"] != phase or payload != scope[phase]:
            raise ValueError("modified, replayed or out-of-order probe state")
        return scope

    @mcp.tool()
    def mathformer_probe_initialize(request: dict, context: dict) -> Initialized:
        with lock:
            root = Path(context["repository_root"]).resolve()
            for relative in (
                "tests/generative/quality_criteria.json",
                "tests/generative/probes/probes.json",
                "artifacts/test_program/generative",
            ):
                if not path_allowed(root / relative):
                    raise ValueError("probe path outside configured service roots")
            parser_output = io.StringIO()
            try:
                with redirect_stdout(parser_output), redirect_stderr(parser_output):
                    args = native.parse_args(request["argv"])
            except SystemExit as error:
                raise ValueError(
                    f"argparse exited {error.code}: {parser_output.getvalue()}"
                ) from error
            state = native.prepare_validation(root)
            if len(state["probes"]) > 10000 or request["probe_count"] != len(
                state["probes"]
            ):
                raise ValueError(
                    "probe_count must match loaded probes within the 10000-probe specialization"
                )
            state["json"] = args.json
            handle = uuid4().hex
            sessions[handle] = dict(
                handle=handle, root=root, phase="state", state=deepcopy(state)
            )
            return dict(state=state, runtime={"handle": handle})

    @mcp.tool()
    def mathformer_probe_inspect_probe(state: dict, runtime: dict) -> Inspected:
        with lock:
            scope = scope_for(runtime, "state", state)
            if not state["has_more"]:
                raise ValueError("probe traversal is exhausted")
            updated = native.inspect_probe(deepcopy(state))
            scope["state"] = deepcopy(updated)
            return {"state": updated}

    @mcp.tool()
    def mathformer_probe_retain_empty(state: dict, runtime: dict) -> Inspected:
        with lock:
            scope_for(runtime, "state", state)
            if (
                state["probes"]
                or state["index"]
                or state["errors"]
                or state["has_more"]
            ):
                raise ValueError("retain_empty requires an empty traversal")
            return {"state": deepcopy(state)}

    @mcp.tool()
    def mathformer_probe_build_report(state: dict, runtime: dict) -> Reported:
        with lock:
            scope = scope_for(runtime, "state", state)
            if state["has_more"]:
                raise ValueError("probe traversal is incomplete")
            report = native.build_report(state)
            scope.update(phase="report", report=deepcopy(report))
            return {"report": report}

    @mcp.tool()
    def mathformer_probe_publish(report: dict, json: bool, runtime: dict) -> Published:
        with lock:
            scope = scope_for(runtime, "report", report)
            if json != scope["state"]["json"]:
                raise ValueError("modified output mode")
            authorize()
            if not path_allowed(scope["root"] / "artifacts/test_program/generative"):
                raise ValueError("probe artifacts outside service write roots")
            output = io.StringIO()
            try:
                with redirect_stdout(output):
                    code = native.publish_report(report, json, scope["root"])
                return {
                    "completion": dict(
                        report_path="artifacts/test_program/generative/probe_validation_report.json",
                        exit_code=code,
                        stdout=output.getvalue(),
                    )
                }
            finally:
                sessions.pop(scope["handle"], None)

    return sessions
