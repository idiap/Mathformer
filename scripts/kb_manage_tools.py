# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Transport adapters for the native premise KB command steps."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict
import manage_premise_kb as native


class Prepared(TypedDict):
    state: dict


class Payload(TypedDict):
    payload: dict
    payload_json: str


class Finished(TypedDict):
    exit_code: int
    stdout: str


GROUPS = {
    "initialize": ("init",),
    "ingest": ("ingest-seeds", "ingest-vampire", "ingest-corpus"),
    "index": ("build-bloom", "build-embeddings"),
    "refresh": ("refresh-canonical",),
    "query": ("has", "search", "distance"),
    "enqueue": ("enqueue-source", "enqueue-web"),
    "curate": ("promote", "reject"),
    "report": ("report",),
}


def register_kb_manage_tools(mcp, guard=lambda path: None):
    @mcp.tool()
    def mathformer_kb_manage_prepare(argv: list[str]) -> Prepared:
        with redirect_stdout(sys.stderr):
            try:
                state = native.prepare(argv)
            except SystemExit as error:
                raise ValueError(f"native argparse exited {error.code}") from error
        return {"state": state}

    def branch(group):
        def invoke(state: dict) -> Payload:
            if state["command"] not in GROUPS[group]:
                raise ValueError("Command does not belong to advertised operation")
            # KB read methods can initialize storage, so guard every dispatch.
            root = Path(state["kb_root"]).resolve()
            if not any(
                root.is_relative_to((native.REPO_ROOT / p).resolve())
                for p in ("artifacts/kb", "artifacts/workflow_hub")
            ):
                raise ValueError("KB root exceeds declared write roots")
            guard(root)
            payload = native.execute_command(state)
            return {
                "payload": payload,
                "payload_json": json.dumps(payload, ensure_ascii=False),
            }

        invoke.__name__ = "mathformer_kb_manage_" + group
        return invoke

    for group in GROUPS:
        mcp.tool()(branch(group))

    @mcp.tool()
    def mathformer_kb_manage_finish(state: dict, payload_json: str) -> Finished:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.finish(state, json.loads(payload_json))
        stdout = stream.getvalue()
        sys.stderr.write(stdout)
        return {"exit_code": code, "stdout": stdout}
