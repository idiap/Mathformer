#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   The independent MCP service config is the boundary that prevents provider
#   credentials from leaking into agent skill environments.
#
# Intent:
#   Exercise config loading, redaction, provider-key bridging, tracked-secret
#   scanning, and MCP tool-surface constraints.
#
# Function:
#   Deterministic test consumed by the mcp module family.
#
# Maintenance Notes:
#   Keep checks synchronized with config/mathformer_mcp.example.toml and
#   scripts/mcp_service_config.py.

"""Test independent Mathformer MCP service configuration."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from mcp_service_config import (  # noqa: E402
    EXAMPLE_CONFIG,
    load_service_config,
    provider_environment,
    redacted_config,
    scan_paths_for_secrets,
    tracked_service_files,
    validate_config,
)


def write_local_config(
    path: Path,
    *,
    token: str = "local-test-token-1234567890",
    api_key: str = "sk-localtest1234567890",
) -> None:
    text = EXAMPLE_CONFIG.read_text(encoding="utf-8")
    text = text.replace('mcp_bearer_token = ""', f'mcp_bearer_token = "{token}"')
    text = text.replace('openai_api_key = ""', f'openai_api_key = "{api_key}"')
    text = text.replace(
        'anthropic_api_key = ""', 'anthropic_api_key = "anthropic-localtest-1234567890"'
    )
    text = text.replace(
        'google_api_key = ""', 'google_api_key = "google-localtest-1234567890"'
    )
    text = text.replace(
        'huggingface_token = ""', 'huggingface_token = "hf-localtest-1234567890"'
    )
    path.write_text(text, encoding="utf-8")


def run_checks() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    missing = load_service_config(
        REPO_ROOT / "config" / "does-not-exist.local.toml", require_existing=True
    )
    checks.append(
        {
            "id": "config.missing_reports_error",
            "ok": not missing.ok
            and any("does not exist" in error for error in missing.errors),
            "detail": list(missing.errors),
        }
    )

    example = load_service_config(EXAMPLE_CONFIG, require_existing=True)
    checks.append(
        {
            "id": "config.example_valid_template",
            "ok": example.ok and example.source_kind == "example",
            "detail": {
                "errors": list(example.errors),
                "warnings": list(example.warnings),
            },
        }
    )

    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / "mathformer_mcp.local.toml"
        secret = "sk-localtest1234567890"
        write_local_config(local_path, api_key=secret)
        local = load_service_config(local_path, require_existing=True)
        checks.append(
            {
                "id": "config.local_valid_with_secret_source",
                "ok": local.ok and local.source_kind == "local",
                "detail": {
                    "errors": list(local.errors),
                    "warnings": list(local.warnings),
                },
            }
        )

        redacted = json.dumps(redacted_config(local), sort_keys=True)
        checks.append(
            {
                "id": "config.redacts_secret_values",
                "ok": secret not in redacted and "<redacted:openai_api_key" in redacted,
                "detail": redacted,
            }
        )

        overridden = load_service_config(
            local_path,
            cli_overrides={"service": {"port": 9999, "readonly": False}},
            require_existing=True,
        )
        checks.append(
            {
                "id": "config.cli_override_precedence",
                "ok": overridden.get("service", "port") == 9999
                and overridden.get("service", "readonly") is False,
                "detail": overridden.data["service"],
            }
        )

        old_values = {
            key: os.environ.pop(key, None)
            for key in (
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GOOGLE_API_KEY",
                "HUGGINGFACE_TOKEN",
            )
        }
        try:
            provider_env = provider_environment(local)
            checks.append(
                {
                    "id": "config.provider_env_from_config_not_process_env",
                    "ok": provider_env.get("OPENAI_API_KEY") == secret
                    and {
                        "OPENAI_API_KEY",
                        "ANTHROPIC_API_KEY",
                        "GOOGLE_API_KEY",
                        "HUGGINGFACE_TOKEN",
                    }
                    <= set(provider_env)
                    and all(key not in os.environ for key in provider_env),
                    "detail": sorted(provider_env),
                }
            )
        finally:
            for key, value in old_values.items():
                if value is not None:
                    os.environ[key] = value

    bad_example = json.loads(json.dumps(example.data))
    bad_example["external_api_keys"]["openai_api_key"] = "sk-badexample1234567890"
    errors, _warnings = validate_config(
        bad_example, path=EXAMPLE_CONFIG, kind="example"
    )
    checks.append(
        {
            "id": "config.example_rejects_nonempty_secrets",
            "ok": any(
                "tracked example config must not set" in error for error in errors
            ),
            "detail": errors,
        }
    )

    findings = scan_paths_for_secrets(tracked_service_files())
    checks.append(
        {
            "id": "config.tracked_files_have_no_live_secrets",
            "ok": not findings,
            "detail": findings,
        }
    )

    docs_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [
            REPO_ROOT / "docs" / "architecture" / "MCP_SERVER.md",
            REPO_ROOT / "docs" / "operations" / "INDEPENDENT_MCP_SERVICE_TODOS.md",
            REPO_ROOT / "AGENTS.md",
        ]
        if path.exists()
    ).lower()
    checks.append(
        {
            "id": "docs.config_is_api_key_source_of_truth",
            "ok": "config/" in docs_text
            and "source of truth" in docs_text
            and "skill-client environment" in docs_text,
            "detail": "service config wording present",
        }
    )

    todo_text = (REPO_ROOT / "TODO.md").read_text(encoding="utf-8")
    checks.append(
        {
            "id": "docs.todo_links_deployment_plan",
            "ok": "docs/operations/INDEPENDENT_MCP_SERVICE_TODOS.md" in todo_text,
            "detail": "main TODO links independent MCP service plan",
        }
    )

    server_text = (REPO_ROOT / "scripts" / "mcp_server.py").read_text(encoding="utf-8")
    tool_names = sorted(
        set(
            part.split("(", 1)[0]
            for part in server_text.split("def ")
            if part.startswith("mathformer_")
        )
    )
    checks.append(
        {
            "id": "mcp.no_direct_script_bypass_tool",
            "ok": "mathformer_run_script" not in tool_names
            and "mathformer_shell" not in tool_names,
            "detail": tool_names,
        }
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        checks = run_checks()
    except Exception as exc:  # noqa: BLE001
        checks = [
            {
                "id": "service_config.unhandled_exception",
                "ok": False,
                "detail": repr(exc),
            }
        ]
    ok = all(item["ok"] for item in checks)
    payload = {"schema_version": 1, "ok": ok, "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in checks:
            print(f"{'PASS' if item['ok'] else 'FAIL'} {item['id']}")
        print(f"{'PASS' if ok else 'FAIL'} mcp_service_config_test")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
