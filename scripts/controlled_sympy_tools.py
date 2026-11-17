# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the shared controlled_suite blocks.

The selected interface is the Python suite, not the hub subprocess envelope.
The service's read-only and write-root policy applies to every writing step.
No providers, subprocess compilers, retries or promotion are introduced.
"""

import json
from pathlib import Path
from typing_extensions import TypedDict


def source():
    from backends.sympy.MathformerPhysicsSympy import pipeline

    return pipeline


class Draft(TypedDict):
    case_id: str
    artifact: str
    draft: dict
    native_json: str


class CaseState(TypedDict):
    items: list[dict]
    native_json: str


class CasesOutput(TypedDict):
    cases: CaseState


class DraftOutput(TypedDict):
    draft: Draft


class ReportOutput(TypedDict):
    report: dict


class GuardOutput(TypedDict):
    done: bool


class SuiteOutput(TypedDict):
    suite: dict


def register_controlled_sympy_tools(mcp, before_write, path_allowed):
    def writing(output_root):
        before_write()
        root = Path(output_root)
        if not path_allowed(root):
            raise ValueError("Controlled SymPy output is outside allowed write roots")
        return root

    def ordered(cases):
        items = json.loads(cases["native_json"])
        if items != cases["items"]:
            raise ValueError("Cases disagree with their native ordered serialization")
        return items

    def state(items):
        return {"items": items, "native_json": json.dumps(items, ensure_ascii=False)}

    def prefix(cases, complete=False):
        cases = ordered(cases)
        ids = source().controlled_case_ids()
        if [row["case_id"] for row in cases] != ids[: len(cases)] or len(cases) > len(
            ids
        ):
            raise ValueError("Cases must be the accumulated native ordered prefix")
        if complete and len(cases) != len(ids):
            raise ValueError("Controlled suite traversal is incomplete")

    @mcp.tool()
    def mathformer_controlled_sympy_initialize(output_root: str) -> CasesOutput:
        return {
            "cases": state(source().controlled_suite_initialize(writing(output_root)))
        }

    @mcp.tool()
    def mathformer_controlled_sympy_generate(
        output_root: str, cases: CaseState
    ) -> DraftOutput:
        root = writing(output_root)
        prefix(cases)
        draft = source().controlled_suite_generate(root, ordered(cases))
        return {
            "draft": {**draft, "native_json": json.dumps(draft, ensure_ascii=False)}
        }

    @mcp.tool()
    def mathformer_controlled_sympy_assess(draft: Draft) -> ReportOutput:
        report = source().controlled_suite_assess(draft)
        return {
            "report": {**report, "native_json": json.dumps(report, ensure_ascii=False)}
        }

    @mcp.tool()
    def mathformer_controlled_sympy_validate_persist_append(
        output_root: str,
        cases: CaseState,
        draft: Draft,
        report: dict,
        include_details: bool,
    ) -> CasesOutput:
        root = writing(output_root)
        prefix(cases)
        items = ordered(cases)
        ids = source().controlled_case_ids()
        if (
            len(items) >= len(ids)
            or draft["case_id"] != ids[len(items)]
            or report["case_id"] != draft["case_id"]
        ):
            raise ValueError("Draft and report must belong to the next controlled case")
        native_draft = json.loads(draft["native_json"])
        native_report = json.loads(report["native_json"])
        if native_draft != {
            key: value for key, value in draft.items() if key != "native_json"
        } or native_report != {
            key: value for key, value in report.items() if key != "native_json"
        }:
            raise ValueError("Payload disagrees with its native ordered serialization")
        return {
            "cases": state(
                source().controlled_suite_append(
                    root, items, native_draft, native_report, include_details
                )
            )
        }

    @mcp.tool()
    def mathformer_controlled_sympy_iteration_guard(cases: CaseState) -> GuardOutput:
        prefix(cases)
        return {"done": source().controlled_suite_done(ordered(cases))}

    @mcp.tool()
    def mathformer_controlled_sympy_finalize(
        output_root: str, cases: CaseState
    ) -> SuiteOutput:
        root = writing(output_root)
        prefix(cases, complete=True)
        return {"suite": source().controlled_suite_finalize(root, ordered(cases))}
