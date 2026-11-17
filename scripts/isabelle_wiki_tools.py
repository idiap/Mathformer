# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native wiki-case steps."""

from functools import lru_cache
import base64
import importlib.util
import json
from pathlib import Path
from typing_extensions import TypedDict


class CaseState(TypedDict):
    output_dir: str
    session_dir: str
    theory_file: str
    latex_file: str
    report: dict


class StateOutput(TypedDict):
    state: CaseState


class ReportOutput(TypedDict):
    report: dict


def transport_state(state, *, unpack=False):
    """Carry TimeoutExpired byte captures without FastMCP's UTF-8 coercion.

    Only subprocess stdout/stderr can be bytes in native state. Keep their
    lossless representation on the wire and restore them before every native
    call. No conversion is applied to the terminal native report: serialization
    errors remain errors, as they are in the CLI's report writer.
    """
    report = state["report"]
    steps = {}
    for name, capture in report["steps"].items():
        capture = dict(capture)
        for field in ("stdout", "stderr"):
            value = capture.get(field)
            if (
                unpack
                and isinstance(value, dict)
                and set(value) == {"mathformer.bytes_base64"}
            ):
                capture[field] = base64.b64decode(
                    value["mathformer.bytes_base64"], validate=True
                )
            elif not unpack and isinstance(value, bytes):
                capture[field] = {
                    "mathformer.bytes_base64": base64.b64encode(value).decode("ascii")
                }
        steps[name] = capture
    return {**state, "report": {**report, "steps": steps}}


@lru_cache(maxsize=1)
def source():
    path = Path(__file__).resolve().parents[1] / "tests/isabelle/run_wiki_case.py"
    spec = importlib.util.spec_from_file_location("mathformer_isabelle_wiki", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register_isabelle_wiki_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    """Expose the shared steps, retaining the service's mutation boundary.

    Paths remain native Path values. All paths carried into a writing step are
    checked, since a caller can invoke individual ports as well as the graph.
    Stage subprocess failures are report data, never an admission condition.
    """

    def admit(*paths):
        before_write()
        if any(not path_allowed(Path(path)) for path in paths):
            raise ValueError("Isabelle wiki writes outside configured service roots")

    def admit_state(state):
        admit(state["output_dir"], state["session_dir"], state["theory_file"])

    @mcp.tool()
    def mathformer_isabelle_wiki_prepare(output_dir: str) -> StateOutput:
        """Create the native output/session directories and report."""
        admit(output_dir)
        return {"state": source().prepare_case(output_dir=Path(output_dir))}

    @mcp.tool()
    def mathformer_isabelle_wiki_ground(state: CaseState) -> StateOutput:
        """Search IsarMathLib with the native command and 60-second bound."""
        admit_state(state)
        return {
            "state": transport_state(
                source().ground_case(state=transport_state(state, unpack=True))
            )
        }

    @mcp.tool()
    def mathformer_isabelle_wiki_draft(state: CaseState) -> StateOutput:
        """Draft the fixed LaTeX fixture with the native command."""
        admit_state(state)
        return {
            "state": transport_state(
                source().draft_case(state=transport_state(state, unpack=True))
            )
        }

    @mcp.tool()
    def mathformer_isabelle_wiki_execute(
        state: CaseState, timeout_sec: int
    ) -> StateOutput:
        """Check the carried theory path using the native Isabelle runner."""
        admit_state(state)
        return {
            "state": transport_state(
                source().execute_case(
                    state=transport_state(state, unpack=True), timeout_sec=timeout_sec
                )
            )
        }

    @mcp.tool()
    def mathformer_isabelle_wiki_finalize(state: CaseState) -> ReportOutput:
        """Return the report with the native exact-true success predicate."""
        report = source().finalize_case(state=transport_state(state, unpack=True))
        # FastMCP otherwise coerces byte values into strings and could silently
        # accept a report the native JSON writer rejects.
        json.dumps(report)
        return {"report": report}
