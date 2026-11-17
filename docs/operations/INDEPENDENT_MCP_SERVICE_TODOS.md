<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Plan the next step from a lightweight in-repo MCP wrapper to an independent
  deployable Mathformer MCP service with explicit dependencies and service
  configuration.

Intent:
  Turn the deployment requirement into concrete, reviewable TODOs before
  implementation, with a hard boundary between service config and agent skill
  environments.

Function:
  Defines phases, acceptance criteria, and validation commands for packaging
  the whole Mathformer pipeline as a standalone MCP service.

Maintenance Notes:
  Keep this synchronized with TODO.md, docs/architecture/MCP_SERVER.md,
  config/, scripts/mcp_server.py, and any future service packaging files.
-->

# Independent MCP Service TODOs

Goal: deploy the whole Mathformer pipeline as an independent MCP service with
all service dependencies, controlled workflow access, and repository-local
configuration for external API keys. The service must not depend on Codex,
Claude, OpenCode, or skill-client environment variables for credentials.

Existing baseline:

- `scripts/mcp_server.py` already exposes the controlled hub over MCP.
- `scripts/mathformer.py` owns workflow actions, safety labels, and NL routes.
- `scripts/install_env.py --with-mcp` installs the current MCP optional extra.
- `config/` now contains tracked examples and ignores local secret files.

## Phase 0: Service Boundary And Threat Model

- [x] Define the independent service as a deployable process rooted at
  `scripts/mcp_server.py`, not as a skill and not as an agent-client plugin.
- [x] Document which workflows are enabled by the service profile:
  Lean, ATP/KB, SymPy physics, MathformerPhysicsLib coherence/foundations,
  docs/report generation, and benchmark/paper workflows.
- [x] Decide default deployment stance:
  `readonly = true`, authenticated HTTP required, stdio allowed for local
  single-client launches.
- [x] Record explicit non-goals:
  no per-skill MCP tools by default, no public unauthenticated endpoint, no
  real API keys in tracked files.
- [x] Add a config-invariant test that fails if service docs or scripts tell
  users to place external API keys only in skill-client environments.

## Phase 1: Config Loader And Validation

- [x] Implement `scripts/load_mcp_service_config.py` or an importable module
  under `scripts/` that reads TOML from `config/mathformer_mcp.local.toml`,
  then overlays explicit CLI flags.
- [x] Support `--config path` on `scripts/mcp_server.py`.
- [x] Validate required fields:
  transport, host, port, readonly, auth policy, rate limit, artifact paths,
  dependency profile, provider names, and external API keys.
- [x] Reject tracked example files when they contain non-empty secret-looking
  values.
- [x] Keep secrets out of command output, audit logs, reasoning logs, and
  generated reports.
- [x] Add `tests/mcp/run_mcp_service_config_test.py` covering:
  missing config, example config, local config, CLI override precedence,
  redaction, and invalid secret placement.

## Phase 2: External API Key Policy

- [x] Define the canonical service key names in
  `config/mathformer_mcp.example.toml`.
- [x] Add provider adapters that read external API keys from the service config
  object, not directly from agent skill environments.
- [x] Add an explicit compatibility bridge only if needed:
  config value may be copied into subprocess environment for third-party SDKs
  at execution time, but the source of truth remains `config/`.
- [x] Add a redaction helper used by MCP responses, config validation, and
  service diagnostics.
- [x] Add tests proving `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and similar
  process environment variables are not required when config provides keys.
- [x] Add tests proving tracked config examples never contain live keys.

## Phase 3: Dependency Closure

- [x] Create a service dependency profile, preferably one of:
  `requirements-mcp-service.txt`, `pyproject.toml` optional extra
  `mcp-service`, or a generated lockfile.
- [x] Include the full pipeline dependency set:
  MCP SDK, HTTP client/server extras, SymPy/NumPy, Docling/PDF extraction,
  benchmark download support, and any provider SDKs selected for generative
  repair or critic workflows.
- [x] Keep Lean/Lake, Vampire, Rocq, and Isabelle as external toolchain checks,
  not Python dependencies.
- [x] Extend `scripts/install_env.py` with `--mcp-service` or equivalent to
  install exactly this profile.
- [x] Add `python scripts/mathformer.py ask "validate independent MCP service dependencies" --run --json`.
- [x] Add a service dependency probe that reports versions, optional-tool
  availability, and missing blockers without importing skill environments.

## Phase 4: Service Entrypoints

- [x] Add a stable launch command:
  `python scripts/mathformer_mcp_service.py --config config/mathformer_mcp.local.toml`.
- [x] Keep `scripts/mcp_server.py` as the MCP implementation, or make the new
  service script a thin wrapper that loads config and calls it.
- [x] Add service manager templates:
  Dockerfile, docker-compose example, and/or systemd unit template.
- [x] Add a startup self-check mode that validates config, dependency profile,
  hub registry, route coverage, MCP tool list, and auth policy without serving.
- [x] Add a read-only smoke deployment command suitable for CI/local validation.

## Phase 5: Whole-Pipeline Workflow Coverage

- [x] Reuse `mathformer-workflow-router` coverage as the service-level route
  inventory gate.
- [x] Add a service coverage report that includes:
  MCP tools, hub actions, intent routes, skill routes, dependencies, and config
  requirements per workflow family.
- [x] Mark workflows that need external tools:
  Lean/Lake, Vampire, Rocq, Isabelle, provider SDKs, and network access.
- [x] Ensure service clients can trigger the full recursive physics
  autoformalization/repair/foundations loop only through controlled hub
  actions.
- [x] Add negative tests for direct script bypass through MCP.

## Phase 6: Security And Operations

- [x] Require auth for HTTP mode by default when using a service config.
- [x] Keep `readonly = true` as the example default; mutating deployments must
  opt in explicitly in local config.
- [x] Add config-controlled artifact roots and refuse writes outside allowed
  roots.
- [x] Add log rotation guidance for `artifacts/mcp_server/calls.jsonl`.
- [x] Add deployment docs for reverse proxy TLS, rate limiting, process
  supervision, and secret injection from files.
- [x] Add a "no secrets in git" validator over `config/`, docs, and service
  templates.

## Phase 7: Documentation And Release Criteria

- [x] Update `docs/architecture/MCP_SERVER.md` with an "Independent Service"
  section that points to `config/` and the service launch command.
- [x] Update README Start Here with the independent service deployment path.
- [x] Update AGENTS.md so agents prefer service config for API keys when the
  task is service deployment.
- [x] Add TODO synchronization checks so this document and `TODO.md` do not
  drift.
- [x] Release criteria:
  - [x] service config validator passes;
  - [x] service dependency probe passes or reports explicit blockers;
  - [x] MCP stdio self-test passes;
  - [x] MCP HTTP auth adversarial test passes;
  - [x] router coverage reports every workflow family covered;
  - [x] hub strict audit passes;
  - [x] no tracked config file contains a live secret;
  - [x] documentation names config files as the API-key source of truth.
