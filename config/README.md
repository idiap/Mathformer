<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Keep independent Mathformer service deployment configuration visible without
  storing secrets in agent skill environments.

Intent:
  Describe the repository-owned config folder for MCP service deployment,
  including tracked examples and ignored local secret files.

Function:
  Guides operators to copy example TOML files into local ignored files and use
  those files as the service configuration source.

Maintenance Notes:
  Keep this synchronized with scripts/mcp_server.py, deployment docs, and the
  independent MCP service release gates in TODO.md.
-->

# Mathformer Service Config

This folder is the configuration root for independent Mathformer MCP service
deployments. It is intentionally separate from Codex, Claude, OpenCode, and
skill-client environments.

Tracked files here should be safe examples or schemas only. Real credentials
must live in ignored local files such as:

- `config/mathformer_mcp.local.toml`
- `config/secrets.local.toml`
- `config/.env`

Start from:

```bash
cp config/mathformer_mcp.example.toml config/mathformer_mcp.local.toml
```

The independent MCP service implementation plan and release gates in
[`docs/operations/INDEPENDENT_MCP_SERVICE_TODOS.md`](../docs/operations/INDEPENDENT_MCP_SERVICE_TODOS.md)
define the service boundary, validation gates, and deployment packaging work.

Validate a local config before serving:

```bash
python scripts/mathformer_mcp_service.py \
  --config config/mathformer_mcp.local.toml --self-check --json
```

Start the service:

```bash
python scripts/mathformer_mcp_service.py --config config/mathformer_mcp.local.toml
```
