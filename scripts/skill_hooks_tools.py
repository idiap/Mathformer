# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP ports for the strict JSON skill-hook validator specialization.

Paths are explicit per invocation; no cwd or global source state is mutated.
The emitter's stdout is captured before it crosses the MCP stdio transport.
"""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py"
)
spec = importlib.util.spec_from_file_location("_skill_hooks_native", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
_EMIT_LOCK = RLock()


class Paths(TypedDict):
    repo_root: str
    hooks_file: str
    skills_dir: str
    prompt_index_file: str


class Resolved(TypedDict):
    paths: Paths
    hooks_exist: bool


class Parsed(TypedDict):
    manifest: dict
    serialized_manifest: str


class Validated(TypedDict):
    findings: list[dict]
    serialized_findings: str


class Reported(TypedDict):
    report: dict
    serialized_report: str


class Emitted(TypedDict):
    stdout: str
    exit_code: int


def register_skill_hooks_tools(mcp):
    """Advertise every operation with its actual named input/output ports."""
    annotations = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    }

    @mcp.tool(name="mathformer_skill_hooks_resolve", annotations=annotations)
    def resolve(repo_root: str) -> Resolved:
        """Resolve the native registered invocation's default paths."""
        args = native.parse_args(["--repo-root", repo_root, "--strict", "--json"])
        paths = native.resolve_hooks_paths(args)
        paths["prompt_index_file"] = str(
            Path(paths["repo_root"]) / args.prompt_index_file
        )
        return {"paths": paths, "hooks_exist": Path(paths["hooks_file"]).exists()}

    @mcp.tool(name="mathformer_skill_hooks_missing_report", annotations=annotations)
    def missing_report(paths: Paths) -> Reported:
        """Return the native early report for a missing hooks manifest."""
        report = native.missing_hooks_report(Path(paths["hooks_file"]))
        return {
            "report": report,
            "serialized_report": json.dumps(report, ensure_ascii=False),
        }

    @mcp.tool(name="mathformer_skill_hooks_parse", annotations=annotations)
    def parse(paths: Paths) -> Parsed:
        """Scan the entire manifest using the source parser."""
        manifest = native.parse_hooks_manifest(Path(paths["hooks_file"]))
        return {
            "manifest": manifest,
            "serialized_manifest": json.dumps(manifest, ensure_ascii=False),
        }

    @mcp.tool(name="mathformer_skill_hooks_validate", annotations=annotations)
    def validate(paths: Paths, manifest: dict, serialized_manifest: str) -> Validated:
        """Accumulate native runtime, hook, route and prompt findings in order."""
        ordered_manifest = json.loads(serialized_manifest)
        if ordered_manifest != manifest:
            raise ValueError("Manifest differs from its source serialization")
        findings = native.validate_manifest(
            ordered_manifest,
            hooks_file=Path(paths["hooks_file"]),
            skills_dir=Path(paths["skills_dir"]),
            repo_root=Path(paths["repo_root"]),
            prompt_index_file=Path(paths["prompt_index_file"]).resolve(),
        )
        return {
            "findings": findings,
            "serialized_findings": json.dumps(findings, ensure_ascii=False),
        }

    @mcp.tool(name="mathformer_skill_hooks_assemble_report", annotations=annotations)
    def assemble_report(
        paths: Paths, manifest: dict, findings: list[dict], serialized_findings: str
    ) -> Reported:
        """Apply the native severity counters and strict report fields."""
        ordered_findings = json.loads(serialized_findings)
        if ordered_findings != findings:
            raise ValueError("Findings differ from their source serialization")
        # Preserve the registered main's no-log helper call before summarization.
        native.validate_reasoning_log_if_requested(
            None, hooks_file=Path(paths["hooks_file"]), strict=True
        )
        report = native.assemble_hooks_report(
            Path(paths["hooks_file"]),
            Path(paths["skills_dir"]),
            manifest,
            ordered_findings,
            strict=True,
        )
        return {
            "report": report,
            "serialized_report": json.dumps(report, ensure_ascii=False),
        }

    @mcp.tool(name="mathformer_skill_hooks_emit", annotations=annotations)
    def emit(report: dict, serialized_report: str) -> Emitted:
        """Capture the full native JSON emission including its final newline."""
        # Lunar canonicalizes object keys between steps. Carry the source's
        # serialization as explicit state to preserve native stdout byte order.
        ordered_report = json.loads(serialized_report)
        if ordered_report != report:
            raise ValueError("Report differs from its source serialization")
        with _EMIT_LOCK, redirect_stdout(io.StringIO()) as stream:
            code = native.emit_hooks_report(
                ordered_report, strict=True, json_output=True
            )
        return {"stdout": stream.getvalue(), "exit_code": code}
