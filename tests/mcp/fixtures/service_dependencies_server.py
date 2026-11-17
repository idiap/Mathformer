# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only installed-metadata/PATH fixtures; production MCP registration intact."""

from tempfile import gettempdir

from pathlib import Path
import contextlib
import io
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from types import SimpleNamespace
from mcp.server.fastmcp import FastMCP
from service_dependency_tools import register_service_dependency_tools

server = SimpleNamespace(mcp=FastMCP("dependency-fixture"))
register_service_dependency_tools(server.mcp)
import probe_mcp_service_dependencies as native

mode, directory = sys.argv[1:]
native.REPO_ROOT = Path(directory)
seen = []


def version(name):
    seen.append(["package", name])
    if mode == "error" and name == "httpx":
        raise RuntimeError("metadata fixture failure")
    if mode == "blocked" or (
        mode == "optional" and name not in ("mcp", "httpx", "uvicorn")
    ):
        raise native.importlib.metadata.PackageNotFoundError(name)
    return "1.2.3"


def which(name):
    seen.append(["tool", name])
    return (
        str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/bin/") + name
        if mode == "ready"
        else None
    )


native.importlib.metadata.version = version
native.shutil.which = which
scope = {
    "__file__": str(ROOT / "scripts/probe_mcp_service_dependencies.py"),
    "__name__": "original_probe",
}
exec(
    (ROOT / "tests/mcp/fixtures/service_dependencies_original.py.txt").read_text(),
    scope,
)
scope["REPO_ROOT"] = native.REPO_ROOT


@server.mcp.tool()
def fixture_original() -> dict:
    seen.clear()
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = scope["main"](["--json"])
    return {
        "report": json.loads(stream.getvalue()),
        "exit_code": code,
        "seen": list(seen),
    }


@server.mcp.tool()
def fixture_seen(reset: bool = False) -> dict:
    result = {"seen": list(seen)}
    if reset:
        seen.clear()
    return result


server.mcp.run(transport="stdio")
