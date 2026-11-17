# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Staged native paper planning, with hub admission, dependency and write audits.

The mount is an explicit execution context, not a replacement implementation.
CLI subprocesses retain their original timeout policy. This in-process tool
family runs the same source functions and returns captured completion data;
transport/Lunar owns invocation budgets. No recorded checklist is executed.
"""

from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import importlib.util
import io
from pathlib import Path
import sys
import traceback
from typing_extensions import TypedDict
import mathformer as hub
from scripts.workflow_write_audit import FileState

ROOT = Path(__file__).resolve().parents[1]
ACTION = "paper:update-plan"
PLANNER = "paper_skills/scientific-paper-drafter/scripts/plan_paper_update.py"
EVIDENCE = "paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py"


def source(path=PLANNER, repository_root=None):
    """Load source code from the checkout, inspecting/writing the selected mount.

    A fresh module keeps simultaneous mounts independent of module globals.
    """
    spec = importlib.util.spec_from_file_location("paper_update_native", ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REPO_ROOT = ROOT if repository_root is None else Path(repository_root)
    return module


def captured(payload, function):
    """Capture native console output and process-like failure once per stage."""
    stdout, stderr = io.StringIO(), io.StringIO()
    value, code = None, 0
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            value = function()
        except SystemExit as error:
            code = error.code if isinstance(error.code, int) else 1
            if error.code and not isinstance(error.code, int):
                print(error.code, file=sys.stderr)
        except Exception:
            code = 1
            traceback.print_exc()
    out, err = stdout.getvalue(), stderr.getvalue()
    # MCP stdout is framing; still expose native console output to the service.
    print(out + err, end="", file=sys.stderr)
    process = hub.complete_leaf_boundary(
        deepcopy(payload),
        code,
        payload.get("stdout", "") + out,
        payload.get("stderr", "") + err,
    )
    return value, process


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class Prepared(TypedDict):
    boundary: dict
    execute: bool


class Loaded(TypedDict):
    process: dict
    loaded: dict
    loaded_ok: bool


class Built(TypedDict):
    process: dict
    plan: dict
    plan_ok: bool


class Process(TypedDict):
    process: dict


class Finished(TypedDict):
    result: dict


def register_paper_update_plan_tools(
    mcp, mount_guard=lambda root: None, write_guard=lambda path: None
):
    def checked_root(name):
        root = Path(name).resolve()
        if not root.is_dir():
            raise ValueError("repository_root must be an existing directory")
        mount_guard(root)
        return root

    @mcp.tool()
    def mathformer_paper_update_prepare(
        context: Context, repository_root: str, extra_args: list[str], seen: list[str]
    ) -> Prepared:
        root = checked_root(repository_root)
        registry = hub.build_registry()
        native = hub.RunContext(**context)

        def dependency(action_id, ancestry):
            # This fixed workflow has one leaf dependency. Its registered argv
            # and preflight/audits remain authoritative; no subprocess fixtures.
            item = registry[action_id]
            admission = hub.admit_action(action_id, registry, (), ancestry)
            if not admission["accepted"]:
                return hub.reject_action(action_id, admission)
            leaf = hub.prepare_leaf_boundary(item, native, (), repository_root=root)
            if not leaf["execute"]:
                return leaf["payload"]
            write_guard(
                root / "artifacts/paper_skills/new_functionality_evidence_packet.json"
            )
            module = source(EVIDENCE, root)
            code, process = captured(
                leaf["payload"], lambda: module.main(list(item.command)[2:])
            )
            if process["ok"]:
                process["returncode"] = code
                process["ok"] = code == 0
            return hub.finish_leaf_boundary(item, leaf, process, repository_root=root)

        prepared = hub.prepare_action(
            ACTION,
            registry,
            native,
            extra_args=extra_args,
            seen=set(seen),
            dependency_runner=dependency,
        )
        boundary = {"prepared": prepared, "repository_root": str(root)}
        if "result" in prepared:
            return {"boundary": boundary, "execute": False}
        leaf = hub.prepare_leaf_boundary(
            registry[ACTION], native, extra_args, repository_root=root
        )
        # Decimal strings keep nanosecond metadata exact across JSON adapters.
        leaf["snapshot"] = {
            path: {
                "size": str(state.size),
                "mtime_ns": str(state.mtime_ns),
                "digest": state.digest,
            }
            for path, state in leaf["snapshot"].items()
        }
        boundary["leaf"] = leaf
        return {"boundary": boundary, "execute": leaf["execute"]}

    @mcp.tool()
    def mathformer_paper_update_load(boundary: dict) -> Loaded:
        root = checked_root(boundary["repository_root"])
        native = source(repository_root=root)
        payload = boundary["leaf"]["payload"]
        loaded, process = captured(
            payload,
            lambda: native.load_inputs(native.parse_options(payload["argv"][2:]), root),
        )
        ready = process["ok"] and loaded is not None
        if ready:
            loaded["process"] = process
        else:
            loaded = {"process": process}
        return {"process": process, "loaded": loaded, "loaded_ok": ready}

    @mcp.tool()
    def mathformer_paper_update_build(loaded: dict) -> Built:
        plan, process = captured(
            loaded["process"], lambda: source().build_plan(loaded["packet"])
        )
        return {
            "process": process,
            "plan": {"value": plan} if process["ok"] else {},
            "plan_ok": process["ok"],
        }

    @mcp.tool()
    def mathformer_paper_update_publish(loaded: dict, plan: dict) -> Process:
        output = Path(loaded["output"])
        write_guard(output)
        write_guard(output.with_suffix(".json"))
        _, process = captured(
            loaded["process"], lambda: source().publish_plan(loaded, plan["value"])
        )
        return {"process": process}

    @mcp.tool()
    def mathformer_paper_update_finish(
        boundary: dict, process: dict | None = None
    ) -> Finished:
        root = checked_root(boundary["repository_root"])
        prepared = boundary["prepared"]
        if "result" in prepared:
            return {"result": prepared["result"]}
        item = hub.build_registry()[ACTION]
        leaf = deepcopy(boundary["leaf"])
        leaf["snapshot"] = {
            path: FileState(int(state["size"]), int(state["mtime_ns"]), state["digest"])
            for path, state in leaf["snapshot"].items()
        }
        if leaf["execute"]:
            if process is None:
                raise ValueError("launched planner requires process completion")
            result = hub.finish_leaf_boundary(item, leaf, process, repository_root=root)
        else:
            result = leaf["payload"]
        return {"result": hub.aggregate_dependencies(item, prepared["state"], result)}


def main():
    """Focused production stdio surface; mounts can be restricted at deployment."""
    import argparse
    from mcp.server.fastmcp import FastMCP

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mount-root", action="append", default=[])
    parser.add_argument("--readonly", action="store_true")
    options = parser.parse_args()
    roots = [Path(p).resolve() for p in options.mount_root] or [ROOT]

    def mount_guard(root):
        if root not in roots:
            raise PermissionError("repository mount outside configured roots")

    def write_guard(path):
        if options.readonly:
            raise PermissionError("paper update writes disabled by read-only policy")
        if not any(
            path.resolve().is_relative_to(root / "artifacts/paper_skills")
            for root in roots
        ):
            raise PermissionError("paper update outside configured artifact roots")

    mcp = FastMCP("mathformer-paper-update-plan")
    register_paper_update_plan_tools(mcp, mount_guard, write_guard)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
