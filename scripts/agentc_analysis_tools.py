# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces over the shared native analyze_logs entrypoint stages."""

from contextlib import redirect_stdout
from dataclasses import asdict
from functools import lru_cache
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py"


@lru_cache(maxsize=1)
def source():
    # Resolve the native sibling import without requiring provider configuration.
    from agentc_workflow_tools import agentc_module

    sys.modules.setdefault("agentc", agentc_module())
    spec = importlib.util.spec_from_file_location(
        "mathformer_analysis_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register_analysis_tools(mcp, before_save=None):
    @mcp.tool()
    def mathformer_analysis_parse(argv: list[str]) -> dict:
        """Parse native analysis CLI options; CLI exits become MCP errors."""
        try:
            with redirect_stdout(sys.stderr):
                return {"options": source().parse_options(argv), "halted": False}
        except SystemExit as error:
            if error.code == 0:
                return {"options": None, "halted": True}
            raise ValueError(
                f"Argument parser exited with status {error.code}"
            ) from error

    @mcp.tool()
    def mathformer_analysis_load(options: dict) -> dict:
        """Read and require a JSON object using the native loader."""
        return {"payload": source()._load_report_payload(options["report_file"])}

    @mcp.tool()
    def mathformer_analysis_coerce(payload: dict) -> dict:
        """Filter fields and construct the native report, including defaults."""
        return {"report": asdict(source()._coerce_report(payload))}

    @mcp.tool()
    def mathformer_analysis_save(report: dict, options: dict) -> dict:
        """Run native statistics collection and JSON then LaTeX writes."""
        if before_save is not None:
            before_save()
        native = source()
        json_path, tex_path, _ = native.save_autoformalization_statistics(
            native.SystematicAutoformalizationReport(**report),
            statistics_file=options["output_json"],
            statistics_tex_file=options["output_tex"],
        )
        return {"paths": {"json": str(json_path), "tex": str(tex_path)}}

    @mcp.tool()
    def mathformer_analysis_finish(paths: dict | None) -> dict:
        """Print native completion paths on stderr, preserving MCP stdout framing."""
        with redirect_stdout(sys.stderr):
            return {"exit_code": source().finish_paths(paths)}
