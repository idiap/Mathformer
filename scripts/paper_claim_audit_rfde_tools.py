# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""RFDE audit stages, retaining a single native subprocess across scan/emit.

Continuation handles are service-local and single use. No serialized command or
filesystem snapshot supplied by a client is trusted for process execution.
"""

import atexit
import subprocess
import tempfile
import uuid
from typing_extensions import TypedDict
import mathformer as hub
from paper_claim_audit_tools import (
    Context,
    AdmissionOutput,
    StateOutput,
    ChildOutput,
    AdvanceOutput,
    ResultOutput,
)

ACTION = "paper:claim-audit-rfde"
PREFIX = "mathformer_paper_claim_audit_rfde_"
MARKER = "__mathformer_audit_scan_complete__\n"
WORKER = """import runpy,sys
sys.argv=sys.argv[1:]
module=runpy.run_path(sys.argv[0])
def checkpoint():
    print('__mathformer_audit_scan_complete__',flush=True)
    if sys.stdin.readline() != 'emit\\n':
        raise RuntimeError('audit continuation abandoned')
raise SystemExit(module['main'](after_scan=checkpoint))
"""


class BoundaryOutput(TypedDict):
    boundary: dict


class AttemptOutput(TypedDict):
    attempt: dict


class GuardOutput(TypedDict):
    run: bool


def register_paper_claim_audit_rfde_tools(mcp, guard=lambda context: None):
    boundaries, attempts = {}, {}

    def item():
        return hub.build_registry()[ACTION]

    def cleanup():
        for record in attempts.values():
            process = record.get("process")
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.communicate()
                record["stderr"].close()
        attempts.clear()
        boundaries.clear()

    atexit.register(cleanup)

    def boundary_record(boundary):
        return boundaries[boundary["continuation"]]

    def capture(record, resume=False):
        process = record["process"]
        stdout, _ = process.communicate("emit\n" if resume else None)
        record["stderr"].seek(0)
        stderr = record["stderr"].read()
        record["stderr"].close()
        record.pop("process")
        payload = hub.complete_leaf_boundary(
            dict(record["payload"]),
            process.returncode,
            record.pop("prefix", "") + stdout,
            stderr,
        )
        record["result"] = payload
        return payload

    @mcp.tool(name=PREFIX + "admit")
    def admit(extra_args: list[str], ancestry: list[str]) -> AdmissionOutput:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, set(ancestry)
            )
        }

    @mcp.tool(name=PREFIX + "reject")
    def reject(admission: dict) -> ResultOutput:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool(name=PREFIX + "initialize")
    def initialize(admission: dict) -> StateOutput:
        return {"state": hub.initialize_dependencies(admission)}

    @mcp.tool(name=PREFIX + "visit")
    def visit(context: Context, state: dict) -> ChildOutput:
        action = item()
        if not 0 <= state["index"] < len(action.depends_on):
            raise ValueError("dependency iterator exhausted")
        guard(context)
        return {
            "child": hub.visit_dependency(
                action, hub.build_registry(), hub.RunContext(**context), state
            )
        }

    @mcp.tool(name=PREFIX + "advance")
    def advance(context: Context, state: dict, child: dict) -> AdvanceOutput:
        updated, done = hub.advance_dependencies(
            item(), state, child, hub.RunContext(**context)
        )
        return {"state": updated, "done": done}

    @mcp.tool(name=PREFIX + "guard")
    def command_guard(context: Context, state: dict) -> GuardOutput:
        return {
            "run": hub.dependency_command_guard(
                item(), state, hub.RunContext(**context)
            )
        }

    @mcp.tool(name=PREFIX + "finish_dependencies")
    def finish_dependencies(state: dict) -> ResultOutput:
        return {"result": hub.finish_dependencies(item(), state)}

    @mcp.tool(name=PREFIX + "prepare")
    def prepare(context: Context) -> BoundaryOutput:
        guard(context)
        boundary = hub.prepare_leaf_boundary(item(), hub.RunContext(**context), ())
        token = uuid.uuid4().hex
        boundaries[token] = dict(boundary=boundary, context=dict(context))
        return {"boundary": dict(boundary, continuation=token)}

    @mcp.tool(name=PREFIX + "scan_main")
    def scan_main(boundary: dict) -> AttemptOutput:
        record = boundary_record(boundary)
        guard(record["context"])
        native = record["boundary"]
        if not native["execute"] or record.get("launched"):
            raise ValueError("boundary is unlaunchable or already launched")
        command = native["payload"]["argv"]
        # Same interpreter, script and arguments; only a checkpoint callback is
        # installed around main. Native stdout/stderr/exit remain source-owned.
        stderr = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        try:
            process = subprocess.Popen(
                [command[0], "-c", WORKER, *command[1:]],
                cwd=hub.REPO_ROOT,
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
            )
        except BaseException:
            stderr.close()
            raise
        record["launched"] = True
        attempt = dict(process=process, stderr=stderr, payload=native["payload"])
        token = uuid.uuid4().hex
        attempts[token] = attempt
        line = process.stdout.readline()
        ready = line == MARKER
        if not ready:
            attempt["prefix"] = line
            capture(attempt)
        return {"attempt": {"ready": ready, "continuation": token}}

    @mcp.tool(name=PREFIX + "emit_main")
    def emit_main(attempt: dict) -> ResultOutput:
        if not attempt["ready"]:
            raise ValueError("scan did not complete")
        record = attempts.pop(attempt["continuation"])
        return {"result": capture(record, resume=True)}

    @mcp.tool(name=PREFIX + "captured_failure")
    def captured_failure(attempt: dict) -> ResultOutput:
        if attempt["ready"]:
            raise ValueError("scan is awaiting emission")
        return {"result": attempts.pop(attempt["continuation"])["result"]}

    @mcp.tool(name=PREFIX + "finish_leaf")
    def finish_leaf(boundary: dict, leaf: dict) -> ResultOutput:
        record = boundaries.pop(boundary["continuation"])
        return {"result": hub.finish_leaf_boundary(item(), record["boundary"], leaf)}

    @mcp.tool(name=PREFIX + "unlaunched")
    def unlaunched(boundary: dict) -> ResultOutput:
        record = boundaries.pop(boundary["continuation"])
        if record["boundary"]["execute"]:
            raise ValueError("boundary requires execution")
        return {"result": record["boundary"]["payload"]}

    @mcp.tool(name=PREFIX + "aggregate")
    def aggregate(state: dict, leaf: dict) -> ResultOutput:
        return {"result": hub.aggregate_dependencies(item(), state, leaf)}
