#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Provide a stable command-line validator for independent Mathformer MCP
#   service configuration.
#
# Intent:
#   Keep service config checks callable from the hub, tests, CI, and operators
#   without exposing secrets.
#
# Function:
#   Delegates to scripts/mcp_service_config.py and preserves its CLI.
#
# Maintenance Notes:
#   Keep this wrapper thin; config behavior belongs in mcp_service_config.py.

"""Validate and display redacted Mathformer MCP service configuration."""

from __future__ import annotations

import sys

from mcp_service_config import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
