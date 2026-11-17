# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Single-use continuations over the example's shared native search generator.

Native runner, candidates and accumulated attempts stay in the service. Public
handles identify a revision and carry the exact native stage observations.
No proof search algorithm or native report assembly is reimplemented here.
"""

import contextlib
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys
import threading
from uuid import uuid4
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "examples/vampire_complex_group_theorem_to_proofs.py"
    )
    spec = importlib.util.spec_from_file_location(
        "mathformer_vampire_group_example", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StatementOutput(TypedDict):
    statement: str


class StateOutput(TypedDict):
    state: dict


class AttemptOutput(TypedDict):
    attempt: dict


class CarryOutput(TypedDict):
    state: dict
    done: bool


class ReportOutput(TypedDict):
    report: dict


class CheckOutput(TypedDict):
    accepted: bool


class CodeOutput(TypedDict):
    code: int


def register_vampire_group_example_tools(mcp, guard=None):
    from backends.atp.MathformerATP.vampire import discover_proof_steps

    sessions = {}
    lock = threading.RLock()

    def check():
        if guard:
            guard()

    def advance(handle, phase):
        session = sessions[handle["token"]]
        if handle != session["handle"] or phase != session["phase"]:
            raise ValueError("stale or out-of-order group example continuation")
        return session

    def handle(token, revision, evidence):
        return dict(token=token, revision=revision, evidence=evidence)

    @mcp.tool()
    def mathformer_group_example_read_statement() -> StatementOutput:
        return {"statement": source().INPUT_PATH.read_text(encoding="utf-8")}

    @mcp.tool()
    def mathformer_group_example_initialize_search(statement: str) -> StateOutput:
        check()
        if statement != source().INPUT_PATH.read_text(encoding="utf-8"):
            raise ValueError("group example requires its fixed repository statement")
        steps = discover_proof_steps(
            statement, artifact_root=source().ARTIFACT_ROOT, time_limit=10
        )
        try:
            event, evidence = next(steps)
            if event != "initialize":
                raise ValueError("unexpected native initialization stage")
            token = uuid4().hex
            public = handle(token, 0, evidence)
            with lock:
                sessions[token] = dict(
                    steps=steps, statement=statement, handle=public, phase="attempt"
                )
            return {"state": public}
        except BaseException:
            steps.close()
            raise

    def event_step(public, phase, expected, following):
        check()
        with lock:
            session = advance(public, phase)
            try:
                event, evidence = next(session["steps"])
                if event != expected:
                    raise ValueError("unexpected native group example stage: " + event)
                updated = handle(public["token"], public["revision"] + 1, evidence)
                session.update(handle=updated, phase=following)
                return updated
            except BaseException:
                sessions.pop(public["token"])["steps"].close()
                raise

    @mcp.tool()
    def mathformer_group_example_direct_attempt(state: dict) -> AttemptOutput:
        attempt = event_step(state, "attempt", "final_attempt", "carry")
        return {"attempt": attempt}

    @mcp.tool()
    def mathformer_group_example_carry_candidate(
        state: dict, attempt: dict
    ) -> CarryOutput:
        with lock:
            session = advance(attempt, "carry")
            if (
                state["token"] != attempt["token"]
                or state["revision"] + 1 != attempt["revision"]
            ):
                raise ValueError("candidate and attempt continuations differ")
            updated = event_step(attempt, "carry", "carry_candidate", "finalize")
            if not updated["evidence"]["done"]:
                session["phase"] = "attempt"
            return {"state": updated, "done": updated["evidence"]["done"]}

    @mcp.tool()
    def mathformer_group_example_finalize_report(
        statement: str, state: dict
    ) -> ReportOutput:
        check()
        with lock:
            session = advance(state, "finalize")
            try:
                if statement != session["statement"]:
                    raise ValueError("statement changed during search")
                try:
                    next(session["steps"])
                except StopIteration as done:
                    return {"report": done.value}
                raise ValueError("native search did not finish")
            finally:
                sessions.pop(state["token"])["steps"].close()

    @mcp.tool()
    def mathformer_group_example_print_and_check(
        statement: str, report: dict
    ) -> CheckOutput:
        # Preserve native text on the diagnostic stream; stdout frames MCP.
        with contextlib.redirect_stdout(sys.stderr):
            return {"accepted": source().print_and_check(statement, report)}

    @mcp.tool()
    def mathformer_group_example_return_code(code: int) -> CodeOutput:
        if code not in (0, 3):
            raise ValueError("example exit code must be 0 or 3")
        return {"code": code}

    return sessions
