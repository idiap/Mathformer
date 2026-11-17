# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP steps backed by the exporter's native Isabelle execution implementation.

A trusted embedding host calls ``registry.open(state, services)`` with its scoped
model, completion and event capabilities, and supplies the returned handle as
workflow input ``services``. The MCP client cannot select credentials, install
callables, or manufacture execution evidence. Keep the registry in the same
worker/session as the host services; close it when that host session ends.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import threading
from types import ModuleType
import uuid
from copy import deepcopy
from typing_extensions import TypedDict


def load_runtime():
    path = Path(__file__).with_name("prism") / "export_mathformer_lunar.py"
    spec = importlib.util.spec_from_file_location("mathformer_lunar_exporter", path)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    runtime = ModuleType("mathformer_lunar_runtime")
    # The authored runtime loads its sibling native adapter through __file__.
    runtime.__file__ = str(path.with_name("mathformer_lunar_runtime.py"))
    exec(compile(exporter.RUNTIME_SOURCE, runtime.__file__, "exec"), runtime.__dict__)
    return runtime


class Initialized(TypedDict):
    evidence: dict
    initial: dict


class Built(TypedDict):
    candidate: dict


class Advanced(TypedDict):
    next: dict
    stop: bool


class Assembled(TypedDict):
    execution: dict


class Verified(TypedDict):
    verification: dict


class IsabelleTraceRegistry:
    """Retain native objects, enforce step order, and reject stale client state."""

    def __init__(self, write_policy, path_allowed):
        self.runtime = load_runtime()
        self.write_policy = write_policy
        self.path_allowed = path_allowed
        self.sessions = {}
        self.lock = threading.RLock()

    def open(self, state, services):
        """Host API: bind an already prepared input to actual host capabilities."""
        self.write_policy()
        if (
            state["workflow_id"] != "isabelle_physics_derivation_trace_loop"
            or state["contract"]["backend"] != "isabelle"
        ):
            raise ValueError("This binding requires the Isabelle trace workflow")
        root = Path(state["run_root"]).resolve(strict=True)
        if not root.is_dir() or not self.path_allowed(root):
            raise ValueError("Run root is outside the authorized host scope")
        if not callable(services.completion) or not callable(services.event):
            raise ValueError("Scoped completion and event capabilities are required")
        token = uuid.uuid4().hex
        with self.lock:
            self.sessions[token] = dict(
                state=deepcopy(state), services=services, phase="reason"
            )
        return {"session_id": token}

    def close(self, handle):
        with self.lock:
            self.sessions.pop(handle["session_id"], None)

    def close_all(self):
        with self.lock:
            self.sessions.clear()

    def invoke(self, handle, phase, function, **values):
        with self.lock:
            token = handle["session_id"]
            if token not in self.sessions:
                raise ValueError("Unknown or closed Isabelle host session")
            session = self.sessions[token]
            try:
                if session["phase"] != phase:
                    raise ValueError("Stale or out-of-order Isabelle step")
                for name, value in values.items():
                    if value != session[name]:
                        raise ValueError("Changed or stale Isabelle " + name)
                self.write_policy()
                return function(session)
            except BaseException:
                self.sessions.pop(token, None)
                raise


def register_isabelle_trace_tools(
    mcp, write_policy=lambda: None, path_allowed=lambda path: True
):
    registry = IsabelleTraceRegistry(write_policy, path_allowed)
    native = registry.runtime

    @mcp.tool()
    def mathformer_isabelle_trace_reason(state: dict, services: dict) -> Initialized:
        """Preflight Isabelle and run the complete native PRISM reasoning graph."""

        def run(s):
            s["native_evidence"], s["attempt"] = native.reason_and_initialize(
                state=s["state"], services=s["services"]
            )
            e = s["native_evidence"]
            s["evidence"] = dict(
                session_id=services["session_id"],
                reasoning_status=e["reasoning_execution"].status,
                completed_steps=e["completed_steps"],
                theory_evidence=e["theory_evidence"],
            )
            s["phase"] = "first"
            return deepcopy({"evidence": s["evidence"], "initial": s["attempt"]})

        return registry.invoke(services, "reason", run, state=state)

    @mcp.tool()
    def mathformer_isabelle_trace_first(
        state: dict, services: dict, attempt: dict, evidence: dict
    ) -> Built:
        """Build the exact graph-produced theory using the native adapter."""

        def run(s):
            s["candidate"] = native.first_build(
                state=s["state"],
                attempt_state=s["attempt"],
                evidence=s["native_evidence"],
            )
            s["phase"] = "record"
            return deepcopy({"candidate": s["candidate"]})

        return registry.invoke(
            services, "first", run, state=state, attempt=attempt, evidence=evidence
        )

    @mcp.tool()
    def mathformer_isabelle_trace_repair(
        state: dict, services: dict, attempt: dict, evidence: dict
    ) -> Built:
        """Run native PRISM repair with original specification and last diagnostics."""

        def run(s):
            s["candidate"] = native.repair_build(
                state=s["state"],
                services=s["services"],
                attempt_state=s["attempt"],
                evidence=s["native_evidence"],
            )
            s["phase"] = "record"
            return deepcopy({"candidate": s["candidate"]})

        return registry.invoke(
            services, "repair", run, state=state, attempt=attempt, evidence=evidence
        )

    @mcp.tool()
    def mathformer_isabelle_trace_record(
        state: dict, services: dict, attempt: dict, candidate: dict
    ) -> Advanced:
        """Retain the request-bound receipt and stop on verification or attempt three."""

        def run(s):
            s["attempt"], stop = native.record_and_advance(
                state=s["state"], attempt_state=s["attempt"], candidate=s["candidate"]
            )
            s["phase"] = "assemble" if stop else "repair"
            return deepcopy({"next": s["attempt"], "stop": stop})

        return registry.invoke(
            services, "record", run, state=state, attempt=attempt, candidate=candidate
        )

    @mcp.tool()
    def mathformer_isabelle_trace_assemble(
        services: dict, attempt: dict, evidence: dict
    ) -> Assembled:
        """Assemble receipts and count the shared initial and repair reasoning events."""

        def run(s):
            s["native_execution"] = native.assemble_execution(
                attempt_state=s["attempt"], evidence=s["native_evidence"]
            )
            e = s["native_execution"]
            s["execution"] = dict(
                receipts=e.receipts,
                reasoning_execution={"status": e.reasoning_execution.status},
                reasoning_result=e.reasoning_result,
                reasoning_event_count=e.reasoning_event_count,
                completed_steps=e.completed_steps,
            )
            s["phase"] = "verify"
            return deepcopy({"execution": s["execution"]})

        return registry.invoke(
            services, "assemble", run, attempt=attempt, evidence=evidence
        )

    @mcp.tool()
    def mathformer_isabelle_trace_verify(
        state: dict, services: dict, execution: dict
    ) -> Verified:
        """Verify retained source hashes and render the source-owned final report."""

        def run(s):
            result = native.verify(state=s["state"], execution=s["native_execution"])
            registry.close(services)
            return {"verification": result}

        return registry.invoke(
            services, "verify", run, state=state, execution=execution
        )

    return registry
