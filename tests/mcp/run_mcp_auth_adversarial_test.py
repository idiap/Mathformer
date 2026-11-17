#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   The streamable-http bearer-token gate in scripts/mcp_server.py was only
#   verified by hand with curl during development; a real deployment depends
#   on it staying correct across future changes.
#
# Intent:
#   Boot the server with --transport streamable-http --auth-token, exercise
#   the no-token/wrong-token/correct-token paths over a real HTTP connection,
#   and fail loudly if the auth gate ever lets an unauthorized request through.
#
# Function:
#   Adversarial deterministic check consumed by
#   tests/test_program/run_comprehensive_tests.py under the `mcp` family.
#
# Maintenance Notes:
#   Keep the expected status codes synchronized with
#   scripts/mcp_server.py's _BearerAuthMiddleware.

"""Adversarial self-test for the MCP server's streamable-http auth gate."""

from __future__ import annotations

import argparse
import json
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until_ready(base_url: str, timeout_seconds: float = 10.0) -> bool:
    import httpx

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            httpx.post(f"{base_url}/mcp", json={}, timeout=1.0)
            return True
        except httpx.HTTPError:
            time.sleep(0.2)
    return False


def run_checks() -> List[Dict[str, Any]]:
    import httpx

    checks: List[Dict[str, Any]] = []
    token = secrets.token_hex(16)
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"

    process = subprocess.Popen(
        [
            PYTHON,
            "scripts/mcp_server.py",
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--auth-token",
            token,
            "--rate-limit",
            "1000",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready = wait_until_ready(base_url)
        checks.append(
            {
                "id": "server.ready",
                "ok": ready,
                "detail": "server did not become ready in time" if not ready else "",
            }
        )
        if not ready:
            return checks

        headers_mcp = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

        no_token = httpx.post(
            f"{base_url}/mcp", json={}, headers=headers_mcp, timeout=5.0
        )
        checks.append(
            {
                "id": "auth.no_token_rejected",
                "ok": no_token.status_code == 401,
                "detail": no_token.status_code,
            }
        )

        wrong_token = httpx.post(
            f"{base_url}/mcp",
            json={},
            headers={**headers_mcp, "Authorization": "Bearer wrong-token"},
            timeout=5.0,
        )
        checks.append(
            {
                "id": "auth.wrong_token_rejected",
                "ok": wrong_token.status_code == 401,
                "detail": wrong_token.status_code,
            }
        )

        correct_token = httpx.post(
            f"{base_url}/mcp",
            json={},
            headers={**headers_mcp, "Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        checks.append(
            {
                "id": "auth.correct_token_passes_gate",
                "ok": correct_token.status_code != 401,
                "detail": correct_token.status_code,
            }
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        checks = run_checks()
    except Exception as exc:  # noqa: BLE001 - surfaced as a failing check, not a crash
        checks = [
            {
                "id": "auth_adversarial.unhandled_exception",
                "ok": False,
                "detail": repr(exc),
            }
        ]

    ok = bool(checks) and all(item["ok"] for item in checks)
    payload = {"schema_version": 1, "ok": ok, "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in checks:
            print(f"{'PASS' if item['ok'] else 'FAIL'} {item['id']}")
        print(f"{'PASS' if ok else 'FAIL'} mcp_auth_adversarial_test")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
