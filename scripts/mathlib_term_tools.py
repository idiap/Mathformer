# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces to the shared native term annotation self-test steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py"
)


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("mathlib_terms_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class State(TypedDict):
    state: dict


class Fixture(TypedDict):
    fixture: dict


class Report(TypedDict):
    report: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Emitted(TypedDict):
    code: int
    stdout: str


def output_path(value: str) -> Path:
    path = Path(value).resolve()
    if path != source().SELF_TEST_OUTPUT.resolve() and not path.is_relative_to(
        (ROOT / "artifacts/workflow_hub").resolve()
    ):
        raise ValueError(
            "term self-test output must be native output or under artifacts/workflow_hub"
        )
    return path


def register_mathlib_term_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_terms_initialize() -> State:
        return {"state": source().initialize_fixture_state()}

    @mcp.tool()
    def mathformer_terms_select_fixture(state: dict) -> Fixture:
        return {"fixture": source().select_fixture(state)}

    @mcp.tool()
    def mathformer_terms_annotate(fixture: dict) -> Report:
        return {"report": source().annotate_text(fixture["text"])}

    @mcp.tool()
    def mathformer_terms_check_append(
        state: dict, fixture: dict, report: dict
    ) -> Advanced:
        state, done = source().check_append(state, fixture, report)
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_terms_write_report(state: dict, output: str) -> Report:
        write_policy()
        return {
            "report": source().write_self_test(state["results"], output_path(output))
        }

    @mcp.tool()
    def mathformer_terms_emit(report: dict, code: int) -> Emitted:
        expected = 0 if report["ok"] else 1
        if code != expected:
            raise ValueError("exit code does not match native report")
        stream = io.StringIO()
        with redirect_stdout(stream):
            actual = source().emit_json(report)
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"code": actual, "stdout": stream.getvalue()}
