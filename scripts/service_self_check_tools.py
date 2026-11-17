# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable diagnostic steps shared with the native self-check entrypoint."""

import dataclasses
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing_extensions import TypedDict

import mathformer_mcp_service as native
from mcp_service_config import ServiceConfig


class Loaded(TypedDict):
    config: dict


class Dependencies(TypedDict):
    dependencies: dict


class Router(TypedDict):
    router: dict


class Audit(TypedDict):
    audit: dict


class Findings(TypedDict):
    findings: list[dict]


class Coverage(TypedDict):
    coverage: dict


class Auth(TypedDict):
    auth: dict


class Report(TypedDict):
    report: dict


class Emitted(TypedDict):
    exit_code: int
    stdout: str


def unpack(config):
    return ServiceConfig(
        data=config["data"],
        source_path=Path(config["source_path"]) if config["source_path"] else None,
        source_kind=config["source_kind"],
        errors=tuple(config["errors"]),
        warnings=tuple(config["warnings"]),
    )


def register_service_self_check_tools(mcp):
    @mcp.tool()
    def mathformer_self_check_load_config(config_path: str) -> Loaded:
        value = native.load_service_config(Path(config_path), require_existing=True)
        packed = dataclasses.asdict(value)
        packed.update(
            source_path=str(value.source_path) if value.source_path else None,
            errors=list(value.errors),
            warnings=list(value.warnings),
            ok=value.ok,
        )
        return {"config": packed}

    @mcp.tool()
    def mathformer_self_check_probe_dependencies() -> Dependencies:
        return {"dependencies": native.dependency_probe()}

    @mcp.tool()
    def mathformer_self_check_router_coverage() -> Router:
        return {"router": native.build_local_router_coverage()}

    @mcp.tool()
    def mathformer_self_check_audit_hub() -> Audit:
        return {"audit": native.hub.audit_control(native.hub.build_registry())}

    @mcp.tool()
    def mathformer_self_check_scan_secrets() -> Findings:
        return {
            "findings": native.scan_paths_for_secrets(native.tracked_service_files())
        }

    @mcp.tool()
    def mathformer_self_check_build_coverage(
        config_path: str, config: dict
    ) -> Coverage:
        return {
            "coverage": native.service_coverage_report(
                Path(config_path), unpack(config).data
            )
        }

    @mcp.tool()
    def mathformer_self_check_evaluate_auth(config: dict) -> Auth:
        return {"auth": native.evaluate_self_check_auth(unpack(config))}

    @mcp.tool()
    def mathformer_self_check_assemble_report(
        config: dict,
        dependencies: dict,
        router: dict,
        audit: dict,
        findings: list[dict],
        coverage: dict,
        auth: dict,
    ) -> Report:
        return {
            "report": native.assemble_self_check_report(
                unpack(config), dependencies, router, audit, findings, coverage, auth
            )
        }

    @mcp.tool()
    def mathformer_self_check_emit(report: dict, exit_code: int) -> Emitted:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_self_check(report, exit_code)
        text = stream.getvalue()
        print(text, end="", file=sys.stderr)
        return {"exit_code": code, "stdout": text}
