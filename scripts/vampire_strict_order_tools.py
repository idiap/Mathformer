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
import io
import time
from vampire_policy_tools import NativeSearch
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
        / "examples/vampire_nontrivial_math_to_proofs.py"
    )
    spec = importlib.util.spec_from_file_location(
        "mathformer_vampire_strict_order", path
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


class CompletionOutput(TypedDict):
    completion: dict


def register_vampire_strict_order_tools(mcp, guard=None):
    sessions = {}
    lock = threading.RLock()

    def check():
        if guard:
            guard()

    def advance(handle, phase):
        session = sessions[handle["token"]]
        if handle != session["handle"] or phase != session["phase"]:
            raise ValueError("stale or out-of-order strict order continuation")
        return session

    def handle(token, revision, evidence):
        return dict(token=token, revision=revision, evidence=evidence)

    @mcp.tool()
    def mathformer_strict_order_read_statement() -> StatementOutput:
        return {"statement": source().INPUT_PATH.read_text(encoding="utf-8")}

    @mcp.tool()
    def mathformer_strict_order_initialize_search(statement: str) -> StateOutput:
        check()
        if statement != source().INPUT_PATH.read_text(encoding="utf-8"):
            raise ValueError("strict order requires its fixed repository statement")
        steps = NativeSearch(
            statement,
            source().ARTIFACT_ROOT,
            time.monotonic() + 180,
            start_method="spawn",
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
                    raise ValueError("unexpected native strict order stage: " + event)
                updated = handle(public["token"], public["revision"] + 1, evidence)
                session.update(handle=updated, phase=following)
                return updated
            except BaseException:
                sessions.pop(public["token"])["steps"].close()
                raise

    @mcp.tool()
    def mathformer_strict_order_direct_attempt(state: dict) -> AttemptOutput:
        attempt = event_step(state, "attempt", "final_attempt", "carry")
        return {"attempt": attempt}

    @mcp.tool()
    def mathformer_strict_order_carry_candidate(
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
    def mathformer_strict_order_finalize_report(
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
    def mathformer_strict_order_present_and_check(
        statement: str, report: dict
    ) -> CompletionOutput:
        stream = io.StringIO()
        try:
            with contextlib.redirect_stdout(stream):
                code = source().present_and_check(statement, report)
        finally:
            # Preserve partial output even when native presentation raises.
            print(stream.getvalue(), end="", file=sys.stderr)
        return {"completion": {"exit_code": code, "stdout": stream.getvalue()}}

    return sessions
