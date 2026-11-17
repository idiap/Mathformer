# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Staged MCP transport for one native generative-critic child process.

The child owns all algorithms, assertions, stdout and exception tracebacks. The
controller only pauses it at source boundaries and applies the existing hub audit.
Children are scoped to this service and reaped when the service exits.
"""

import atexit
from copy import deepcopy
from dataclasses import asdict
import os
from pathlib import Path
import subprocess
import sys
import uuid
from typing_extensions import TypedDict
import mathformer as hub
from coherence_suite_tools import Context
from scripts.workflow_write_audit import FileState

ACTION = "mathformerphysicslib:generative-coherence-critic"
ROOT = Path(__file__).resolve().parents[1]


class BoundaryResult(TypedDict):
    boundary: dict


class StateResult(TypedDict):
    state: dict


class ChildResult(TypedDict):
    child: dict


class Result(TypedDict):
    result: dict


class Child:
    def __init__(self, boundary):
        environment = dict(os.environ)
        environment["MATHFORMER_GENERATIVE_STAGE_IO"] = "1"
        environment["MATHFORMER_GENERATIVE_REPOSITORY_ROOT"] = boundary[
            "repository_root"
        ]
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        self.process = subprocess.Popen(
            boundary["payload"]["argv"],
            cwd=ROOT,
            env=environment,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.stderr = ""
        self.state = None

    def read(self, stage):
        marker = "mathformer-stage:" + stage + ":"
        while True:
            line = self.process.stderr.readline()
            if line.startswith(marker):
                return line[len(marker) :].rstrip("\n")
            if not line:
                return None
            self.stderr += line

    def resume(self, stage):
        self.process.stdin.write(stage + "\n")
        self.process.stdin.flush()

    def finish(self):
        stdout, stderr = self.process.communicate()
        result = dict(
            returncode=self.process.returncode,
            stdout=stdout,
            stderr=self.stderr + stderr,
        )
        # Preserve native output on the service diagnostic channel too.
        print(stdout, end="", file=sys.stderr)
        print(result["stderr"], end="", file=sys.stderr)
        return result

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.communicate()


CHILDREN = {}


def cleanup():
    for child in list(CHILDREN.values()):
        child.close()
    CHILDREN.clear()


atexit.register(cleanup)


def checked(state):
    child = CHILDREN[state["token"]]
    if state != child.state:
        raise ValueError("staged state differs from the observed native child state")
    return child


def register_generative_critic_tools(mcp):
    @mcp.tool()
    def mathformer_generative_critic_prepare(
        context: Context, repository_root: str, extra_args: list[str], seen: list[str]
    ) -> BoundaryResult:
        registry = hub.build_registry()
        admission = hub.admit_action(ACTION, registry, extra_args, seen)
        root = str(Path(repository_root).resolve(strict=True))
        if not admission["accepted"]:
            boundary = dict(
                execute=False, payload=hub.reject_action(ACTION, admission), snapshot={}
            )
        else:
            boundary = hub.prepare_leaf_boundary(
                registry[ACTION],
                hub.RunContext(**context),
                extra_args,
                repository_root=Path(root),
            )
        boundary["snapshot"] = {
            path: asdict(value) for path, value in boundary["snapshot"].items()
        }
        return {"boundary": {**boundary, "repository_root": root}}

    @mcp.tool()
    def mathformer_generative_critic_return_without_launch(boundary: dict) -> Result:
        if boundary["execute"]:
            raise ValueError("boundary requires launch")
        return {"result": boundary["payload"]}

    @mcp.tool()
    def mathformer_generative_critic_default_reports(boundary: dict) -> StateResult:
        if not boundary["execute"]:
            raise ValueError("boundary does not admit launch")
        expected = hub.resolve_command(hub.build_registry()[ACTION].command)
        if boundary["payload"]["argv"] != expected:
            raise ValueError("only the registered fixed argv may be launched")
        child = Child(boundary)
        token = uuid.uuid4().hex
        CHILDREN[token] = child
        encoded = child.read("reports")
        state = dict(
            token=token, reports_json=encoded or "[]", plan_json="{}", child={}
        )
        if encoded is None:
            state["child"] = child.finish()
            del CHILDREN[token]
        child.state = deepcopy(state)
        return {"state": state}

    @mcp.tool()
    def mathformer_generative_critic_plan(state: dict) -> StateResult:
        if state["child"]:
            return {"state": state}
        child = checked(state)
        child.resume("reports")
        encoded = child.read("plan")
        updated = {**state, "plan_json": encoded or "{}"}
        if encoded is None:
            updated["child"] = child.finish()
            del CHILDREN[state["token"]]
        child.state = deepcopy(updated)
        return {"state": updated}

    @mcp.tool()
    def mathformer_generative_critic_complete_child(state: dict) -> ChildResult:
        if state["child"]:
            return {"child": state["child"]}
        child = checked(state)
        child.resume("plan")
        result = child.finish()
        del CHILDREN[state["token"]]
        return {"child": result}

    @mcp.tool()
    def mathformer_generative_critic_finish(boundary: dict, child: dict) -> Result:
        payload = {
            **boundary["payload"],
            **child,
            "status": "completed",
            "ok": child["returncode"] == 0,
        }
        restored = {
            **boundary,
            "snapshot": {
                path: FileState(**value) for path, value in boundary["snapshot"].items()
            },
        }
        return {
            "result": hub.finish_leaf_boundary(
                hub.build_registry()[ACTION],
                restored,
                payload,
                repository_root=Path(boundary["repository_root"]),
            )
        }

    # Composed aliases share the registered implementations and their live child
    # table; they must never launch replacement per-stage processes.
    return {
        "prepare": mathformer_generative_critic_prepare,
        "skip": mathformer_generative_critic_return_without_launch,
        "reports": mathformer_generative_critic_default_reports,
        "plan": mathformer_generative_critic_plan,
        "complete": mathformer_generative_critic_complete_child,
        "finish": mathformer_generative_critic_finish,
    }
