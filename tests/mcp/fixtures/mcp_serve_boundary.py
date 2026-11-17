# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external serving boundary. Native setup/middleware stays real."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import mcp_server as native
import uvicorn


def install():
    def stdio(**kwargs):
        assert kwargs == {"transport": "stdio"}
        assert native._READONLY in (True, False)

    def http(app, *, host, port):
        assert native.mcp.settings.host == host
        assert native.mcp.settings.port == port
        if port == 9999:
            raise RuntimeError("deterministic serving failure")
        assert isinstance(
            app, (native._BearerAuthMiddleware, native._RateLimitMiddleware)
        ) or callable(app)

    native.mcp.run = stdio
    uvicorn.run = http


if __name__ == "__main__":
    transport = native.mcp.run
    install()
    transport(transport="stdio")
