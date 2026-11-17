# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP steps shared with the independent service configuration CLI."""

from contextlib import redirect_stdout
import dataclasses
import io
from pathlib import Path
import sys
from typing import TypedDict

import mcp_service_config as native


class Parsed(TypedDict):
    options: dict


class Loaded(TypedDict):
    config: dict


class Scanned(TypedDict):
    findings: list[dict]


class Reported(TypedDict):
    report: dict


class Emitted(TypedDict):
    exit_code: int
    stdout: str


def register_service_config_tools(mcp):
    @mcp.tool()
    def mathformer_service_config_parse(argv: list[str]) -> Parsed:
        # Argparse prints help/usage before exiting. MCP reserves stdout for framing.
        with redirect_stdout(sys.stderr):
            try:
                return {"options": native.parse_service_options(argv)}
            except SystemExit as error:
                raise ValueError(f"argparse exited with status {error.code}") from error

    @mcp.tool()
    def mathformer_service_config_load(options: dict, repo_root: str) -> Loaded:
        config = native.load_service_config(
            options["config"],
            require_existing=options["require_existing"],
            repo_root=Path(repo_root),
        )
        value = dataclasses.asdict(config)
        value["source_path"] = (
            str(config.source_path) if config.source_path is not None else None
        )
        value["errors"], value["warnings"] = list(config.errors), list(config.warnings)
        return {"config": value}

    @mcp.tool()
    def mathformer_service_config_scan(repo_root: str) -> Scanned:
        root = Path(repo_root)
        return {
            "findings": native.scan_paths_for_secrets(
                native.tracked_service_files(repo_root=root), repo_root=root
            )
        }

    @mcp.tool()
    def mathformer_service_config_no_scan() -> Scanned:
        return {"findings": []}

    @mcp.tool()
    def mathformer_service_config_report(
        config: dict, findings: list[dict], repo_root: str
    ) -> Reported:
        value = native.ServiceConfig(
            data=config["data"],
            source_path=(
                Path(config["source_path"])
                if config["source_path"] is not None
                else None
            ),
            source_kind=config["source_kind"],
            errors=tuple(config["errors"]),
            warnings=tuple(config["warnings"]),
        )
        return {
            "report": native.finish_service_report(
                value, findings, repo_root=Path(repo_root)
            )
        }

    @mcp.tool()
    def mathformer_service_config_emit(options: dict, report: dict) -> Emitted:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_service_report(options, report)
        text = stream.getvalue()
        print(text, end="", file=sys.stderr)
        return {"exit_code": code, "stdout": text}
