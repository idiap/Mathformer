# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Process-local, ordered MCP bindings for the native parallel verifier."""

from __future__ import annotations

import atexit
from pathlib import Path
import threading
import uuid
from typing_extensions import TypedDict
import importlib.util
import sys

_spec = importlib.util.spec_from_file_location(
    "mathformer_parallel_verifier",
    Path(__file__).with_name("prism") / "verify_mathformer_prism.py",
)
native = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = native
_spec.loader.exec_module(native)
VerificationSession = native.VerificationSession
require = native.require

ROOT = Path(__file__).resolve().parents[1]


class StateOutput(TypedDict):
    state: dict


class IterationOutput(TypedDict):
    state: dict
    done: bool


class ReportOutput(TypedDict):
    report: dict


def register_prism_verification_tools(mcp, write_policy=lambda: None):
    sessions = {}
    lock = threading.RLock()

    def close_all():
        for session, _ in list(sessions.values()):
            session.close()
        sessions.clear()

    atexit.register(close_all)

    def advance(state, phase, method, next_phase, iterative=False):
        with lock:
            token = state.get("session_id")
            require(token in sessions, "unknown or closed verifier session")
            session, expected = sessions[token]
            try:
                require(
                    state == expected and state["phase"] == phase,
                    "stale or out-of-order verifier state",
                )
                done = getattr(session, method)()
                target = next_phase if not iterative or done else phase
                packed = {
                    "session_id": token,
                    "phase": target,
                    "cursor": session.cursor,
                }
                sessions[token] = (session, packed)
                if method == "write_report":
                    del sessions[token]
                    return {"report": done}
                return {"state": packed, **({"done": done} if iterative else {})}
            except BaseException:
                session.close()
                sessions.pop(token, None)
                raise

    @mcp.tool()
    def mathformer_prism_initialize(config: dict, context: dict) -> StateOutput:
        """Fingerprint and validate catalog identity in an explicit working directory."""
        write_policy()
        base = Path(context["working_directory"]).resolve()
        require(base.is_relative_to(ROOT), "working directory is outside repository")
        require(
            config["root"] == "mathformer-prism"
            and config["jobs"] == 4
            and config["handler"] == "codex"
            and config["selected_workflows"] is None
            and config["report_path"]
            == "mathformer-prism/tests/native-semantic-parallel-e2e.json",
            "configuration differs from specialized hub route",
        )
        root = (base / config["root"]).resolve()
        output = (base / config["report_path"]).resolve()
        require(
            root.is_relative_to(base) and output.is_relative_to(root),
            "path escapes working directory",
        )
        session = VerificationSession(
            root, config["prism_bin"], config["jobs"], output, config["handler"]
        )
        require(
            len(session.entries) == 14,
            "specialized route requires exactly 14 catalog entries",
        )
        token = uuid.uuid4().hex
        state = {"session_id": token, "phase": "catalog", "cursor": 0}
        with lock:
            sessions[token] = (session, state)
        return {"state": state}

    @mcp.tool()
    def mathformer_prism_validate_entry(state: dict) -> IterationOutput:
        """Validate the next catalog record, including native negative controls."""
        return advance(state, "catalog", "validate_entry", "submit", True)

    @mcp.tool()
    def mathformer_prism_prepare_runtime(state: dict) -> StateOutput:
        """Validate inventory and submit every selected native run before awaiting."""
        write_policy()
        return advance(state, "submit", "prepare_runtime", "await")

    @mcp.tool()
    def mathformer_prism_await_entry(state: dict) -> IterationOutput:
        """Await one future in submission order and accumulate runtime failures."""
        return advance(state, "await", "await_entry", "join", True)

    @mcp.tool()
    def mathformer_prism_finish_runtime(state: dict) -> StateOutput:
        """Join and release resources; propagate accumulated runtime failures."""
        return advance(state, "join", "finish_runtime", "report")

    @mcp.tool()
    def mathformer_prism_write_report(state: dict) -> ReportOutput:
        """Check concurrency and unchanged sources before writing the native report."""
        write_policy()
        return advance(state, "report", "write_report", "closed")

    @mcp.tool()
    def mathformer_prism_close(state: dict) -> dict:
        """Release an interrupted session, joining all submitted work before cleanup."""
        with lock:
            found = sessions.pop(state.get("session_id"), None)
            if found:
                found[0].close()
        return {"closed": True}

    return close_all
