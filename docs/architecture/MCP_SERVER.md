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
  Let MCP-aware clients reach Mathformer without learning repository-specific
  script names, while documenting deployment as its own concern separate from
  the README quickstart.

Intent:
  Explain what the MCP server exposes, how to install and run it locally, how
  to configure common MCP clients, the safety model it inherits from the
  workflow hub, and the remote/shared deployment option.

Function:
  Companion deployment guide for scripts/mcp_server.py. Linked from the
  README "Start Here" list rather than duplicated there.

Maintenance Notes:
  Keep the tool list and safety model description synchronized with
  scripts/mcp_server.py and scripts/mathformer.py's action registry.
-->

# Mathformer MCP Server

Mathformer can be reached from any [Model Context Protocol](https://modelcontextprotocol.io)
(MCP) client — Claude Desktop, Claude Code, or another MCP-aware agent —
through `scripts/mcp_server.py`. It wraps the same controlled workflow hub
used by `scripts/mathformer.py ask`, so MCP clients get one small, audited
tool surface instead of one tool per skill.

## Status

Tracked against the "Lightweight MCP Server For Skills (Workflow-Level
Access)" section of `TODO.md`. Keep this section, the independent service
TODOs, and that TODO section synchronized whenever the MCP deployment surface
changes.

Shipped:

- The nine-tool/six-resource surface and workflow resource template described below, verified end-to-end
  over a real stdio client/server handshake, not just direct in-process
  dispatch.
- The unchanged hub safety model (`read_only`/`writes_artifacts`/
  `writes_environment`/`writes_repo` plus `allow_mutating`).
- `stdio` (default) and `streamable-http` transports.
- Deterministic test coverage: `tests/mcp/run_mcp_server_self_test.py` and
  `tests/mcp/run_mcp_auth_adversarial_test.py`, registered under the `mcp`
  module family, reachable through `quality:smoke` (via `test:quick`) and
  `quality:full` (via `test:comprehensive`), and skipped rather than failed
  when the optional `mcp` dependency is absent.
- A tool/CLI drift meta-test (`tools.cli_sync`) that fails if
  `scripts/mcp_server.py`'s tools and `scripts/mathformer.py`'s subcommands
  go out of sync.
- An explicit, documented decision not to wrap MCP calls in reasoning-log
  instrumentation (see Observability below), plus a lighter-weight JSONL
  call log as the chosen alternative.
- `--readonly`, `--auth-token`/`MATHFORMER_MCP_TOKEN`, and `--rate-limit` for
  `--transport streamable-http`, each verified directly (curl for the manual
  pass, an automated adversarial test for the auth gate).
- A default execution timeout ceiling for the ~49 leaf actions that declared
  no `timeout_seconds`, applied only to execution, not to what
  `mathformer_list_actions`/`mathformer_show_action`/the resource report.

Not done / explicitly out of scope for now:

- Per-skill MCP tools (see Scope And Non-Goals below — declined by design,
  not a gap).
- Distributed (multi-instance) rate limiting; the current limiter is
  per-process (see Concurrency And Resource Limits below).
- A per-action-id write lock for concurrent calls to the same action; see
  Concurrency And Resource Limits for why this was a deliberate non-fix
  rather than an oversight.

## What It Exposes

Six MCP tools, all backed by the in-process hub in `scripts/mathformer.py`.
Five mirror the CLI 1:1; help and normalized workflow tools are MCP-native, with no CLI
equivalent, and is the recommended first call:

| Tool | Equivalent CLI command | Purpose |
| --- | --- | --- |
| `mathformer_help` | *(none — MCP-native)* | List the curated natural-language workflow catalogue (title/description/examples). Call this first. |
| `mathformer_ask` | `mathformer.py ask "..."` | Resolve a natural-language goal to a controlled route, optionally run it |
| `mathformer_list_actions` | `mathformer.py list` | List the full low-level action registry and safety labels |
| `mathformer_show_action` | `mathformer.py show ID` | Show one action's full contract (command, writes, dependencies) |
| `mathformer_run_action` | `mathformer.py run ID` | Run one action id directly, bypassing NL routing |
| `mathformer_audit` | `mathformer.py audit` | Audit that repository entrypoints are controlled |
| `mathformer_list_workflows` | *(MCP-native)* | List/filter the complete normalized workflow catalog |
| `mathformer_show_workflow` | *(MCP-native)* | Read a full YAML contract by canonical ID or explicit alias |
| `mathformer_run_workflow` | *(MCP-native)* | Dispatch native hub/route bindings through existing execution controls |

`mathformer_help` returns the same curated routes `mathformer_ask` matches
against (`hub.build_intent_routes()`) — titles, descriptions, and example
phrasing — rather than the full ~90-entry action registry, so a client can
get oriented without parsing low-level command/safety/dependency metadata
it doesn't need yet. Reach for `mathformer_list_actions` only when you need
that low-level detail.

Four read-only resources are available:

| Resource | Purpose |
| --- | --- |
| `mathformer://actions` | Full action catalogue as JSON, equivalent to `mathformer.py list --json` |
| `mathformer://reasoning-logs` | Stable reasoning-log index from `artifacts/reasoning/index.json`, or the controlled action id needed to build it |
| `mathformer://reasoning-log-schema` | The schema reference, including the consumer-grade profile |
| `mathformer://reasoning-log-quality-policy` | Machine-readable quality dimensions, blocking findings, and resource policy |

Reasoning-log resources do not expose arbitrary file reads. Individual log
inspection stays gated by the stable index and by controlled hub actions such
as `control:reasoning-log-summary`, `control:reasoning-log-quality`, and
`control:reasoning-log-html`.

Skills are not exposed as individual MCP tools. `mathformer_ask` already
returns the relevant `skill_routes` for a matched intent; adding one separate
tool for every skill would bloat every client's tool list and degrade tool
selection instead of helping it.

Meta-skills follow the same boundary. The MCP service exposes meta-skill
registry lookup, taxonomy navigation, runtime-trace validation, and generated
skill promotion checks only as workflow-level hub actions, never as direct
draft generated-skill tools. The policy is validated by
`python meta_skills/scripts/validate_mcp_boundary.py --json`.

## Scope And Non-Goals

`scripts/mcp_server.py` is intentionally not a skill. It has no
`skills/mcp-server/SKILL.md` and no entry in `skills/SKILL_HOOKS.yaml`, and it
is exempt from `skill-hook-coverage-maximizer`'s coverage requirement, because
it is a cross-cutting deployment surface over the hub rather than a reusable
agent workflow. Its own correctness is covered separately by the `mcp`
module-family test (see Testing below), not by the skill-hook contract.

Per-skill MCP tools are out of scope by default. `mathformer_ask`'s
`skill_routes` field stays the only skill-discovery path for MCP clients
unless a real client integration proves the workflow-level routing
insufficient; this avoids re-litigating the tool-list bloat problem one skill
at a time.

## Safety Model

MCP access does not grant extra permission beyond the CLI. Every tool call
goes through the same `RunContext` and preflight checks as
`mathformer.py ask`/`run`:

- `read_only` actions execute freely.
- `writes_artifacts` actions write only to the gitignored `artifacts/` tree.
- `writes_environment` and `writes_repo` actions are blocked unless the caller
  passes `allow_mutating=True` on that specific tool call (or `dry_run=True`
  to preview the command without executing it).

There is no server-wide "trust this client" switch — mutation intent is
declared per call, exactly like `--allow-mutating` on the CLI.

## Observability And Audit Trail

MCP-triggered runs are deliberately **not** wrapped with
`skills/control/reasoning-log-schema-guardian`'s reasoning-log instrumentation. That
schema is scoped to skill executions (`payload.skill`, hook id, monotone event
index) and the hub itself does not emit reasoning-log events for any caller
today, including the CLI — `mathformer.py run`/`ask` has never gone through
that pipeline. Bolting it on only for MCP would create an inconsistency
between CLI and MCP observability rather than fixing a real gap; if hub-level
reasoning-log coverage is ever added, it should cover both callers at once.

Instead, every `mathformer_run_action` call and every
`mathformer_ask(run=True)` call appends one line to
`artifacts/mcp_server/calls.jsonl` recording the action id (or resolved route
id), safety label, `allow_mutating`, `dry_run`, the resulting `ok` value, and
a UTC timestamp. This is a lightweight audit trail for a shared deployment,
not a full trajectory/observability surface — read-only `mathformer_ask`
(without `run=True`), `mathformer_list_actions`, `mathformer_show_action`, and
`mathformer_audit` are not logged, since they cannot mutate anything.

The log lives under the gitignored `artifacts/` tree, like every other
generated report in this repository. It is append-only with no automatic
rotation; for a long-lived shared deployment, rotate or truncate
`artifacts/mcp_server/calls.jsonl` out-of-band (for example with `logrotate`
or a periodic cron job), the same way you would for any other
append-only service log.

Reasoning-log consumption itself is exposed through workflow-level actions and
resources, not through MCP call instrumentation. A consumer can call
`mathformer_ask("run the reasoning-log consumer-readiness checks", run=True)`
or `mathformer_run_action("control:reasoning-log-consumer-readiness")` to
build `artifacts/reasoning/index.json`, then read
`mathformer://reasoning-logs` for discoverable log summaries. This keeps CLI
and MCP behavior symmetric: the hub owns generation and validation, while MCP
only routes to the hub or reads the stable resources.

The redaction policy is enforced by
`skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py`:
consumer-facing logs, summaries, rendered views, and MCP resource payloads
must avoid bearer tokens, API keys, passwords, raw credentials, unnecessary
private paths, hidden chain-of-thought, and oversized inline stdout/stderr.

## Install

The MCP Python SDK is an opt-in extra, not part of the default install:

```bash
uv run python scripts/install_env.py --with-mcp
```

It is also included by `--all-extras`.

## Run Locally (stdio)

Most MCP clients spawn the server process themselves and talk to it over
stdio. Point the client at this command:

```bash
python3 scripts/mcp_server.py
```

Do not run it via `mathformer.py run mcp:serve` in a client config: the hub's
`run_action()` buffers subprocess output until the process exits and does not
proxy stdin interactively, which breaks the stdio protocol. The hub entry
exists only so `mathformer_ask`/`mathformer_list_actions` can describe and
audit the server; client configs should launch `scripts/mcp_server.py`
directly, as shown below.

### Claude Code

From the checkout, set `MATHFORMER_ROOT="$(pwd)"` before running these commands.

```bash
claude mcp add mathformer -- python3 "${MATHFORMER_ROOT}/scripts/mcp_server.py"
```

Use the repository's `.venv` interpreter instead of a bare `python3` if the
`mcp` extra was installed there:

```bash
claude mcp add mathformer -- "${MATHFORMER_ROOT}/.venv/bin/python" "${MATHFORMER_ROOT}/scripts/mcp_server.py"
```

### Claude Desktop

Add a server entry to `claude_desktop_config.json`. Replace `${MATHFORMER_ROOT}`
with the resolved checkout directory; JSON configuration does not expand shell variables:

```json
{
  "mcpServers": {
    "mathformer": {
      "command": "${MATHFORMER_ROOT}/.venv/bin/python",
      "args": ["scripts/mcp_server.py"],
      "cwd": "${MATHFORMER_ROOT}"
    }
  }
}
```

Restart Claude Desktop after editing the config so it reloads the server
list.

### Other MCP Clients

Any client that can spawn a stdio MCP server (Cursor, OpenCode, custom SDK
clients) follows the same pattern: command = the venv Python, args =
`["scripts/mcp_server.py"]`, working directory = the repository root.

## Run Remotely (streamable-http)

For a shared deployment reachable over a network instead of spawned per
client:

```bash
MATHFORMER_MCP_TOKEN=$(openssl rand -hex 32) \
  python3 scripts/mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8765
```

This starts a long-running HTTP server with three independent hardening
controls, all opt-in flags rather than separate code paths:

- **Auth**: pass `--auth-token TOKEN` or set `MATHFORMER_MCP_TOKEN` to require
  a matching `Authorization: Bearer TOKEN` header on every request; requests
  without it get `401`. This is a single static shared secret, not OAuth —
  deliberately lighter weight than FastMCP's built-in `mcp.server.auth`
  subsystem, which requires a full OAuth issuer URL even for one secret. If
  no token is configured, the server starts anyway but prints a stderr
  warning, since requiring a token by default would silently break existing
  stdio-only setups that pass the same CLI flags.
- **Rate limiting**: `--rate-limit N` (default `60`) caps requests per client
  IP per minute with an in-process sliding window; excess requests get `429`.
  Pass `--rate-limit 0` to disable it. This guards one server instance
  against one client looping a long-running action through
  `mathformer_run_action`; it is not distributed, so a multi-instance
  deployment behind a load balancer still needs the reverse-proxy rate
  limiting noted below.
- **Read-only mode**: `--readonly` forces every tool call to behave as
  `allow_mutating=False` regardless of what the caller passes, for
  deployments that should never accept a mutating call at all — for example
  a shared catalogue browser where only `mathformer_ask`/`mathformer_list_actions`/
  `mathformer_show_action`/`mathformer_audit` are meant to be used.

None of these replace standard network hardening:

- Still run it behind a reverse proxy that terminates TLS; the token check
  above protects against unauthorized tool calls, not transport-level
  eavesdropping of an unencrypted connection.
- Bind to `127.0.0.1` instead of `0.0.0.0` unless the deployment is meant to
  be reachable from other hosts.
- The safety model above still applies per call, but a shared deployment
  means every client holding the token shares the same `allow_mutating` trust
  boundary unless `--readonly` is set — only deploy this way for trusted
  internal use, not as a public endpoint.
- Treat the process like the other long-running build/test workflows in this
  repository: run it under a process supervisor (systemd, a container
  orchestrator) rather than a bare foreground shell if it needs to stay up.

## Independent Whole-Pipeline Service

For a deployable service profile, use `scripts/mathformer_mcp_service.py`
instead of calling `scripts/mcp_server.py` directly. The service wrapper loads
repository-local TOML config, validates the dependency/profile boundary, and
then delegates to the same MCP implementation.

Create a local ignored config:

```bash
cp config/mathformer_mcp.example.toml config/mathformer_mcp.local.toml
```

Set external API keys in `config/mathformer_mcp.local.toml`, not in Codex,
Claude, OpenCode, or skill-client environment files. The service config is the
source of truth; if a third-party SDK needs an environment variable, the service
bridges the config value into the process environment at startup.

Run a startup self-check without serving:

```bash
python scripts/mathformer_mcp_service.py \
  --config config/mathformer_mcp.local.toml --self-check --json
```

Start the service:

```bash
python scripts/mathformer_mcp_service.py --config config/mathformer_mcp.local.toml
```

Install the service Python profile:

```bash
uv run python scripts/install_env.py --mcp-service
```

Deployment templates live under `deploy/mcp/`:

Export `MATHFORMER_CONTAINER_ROOT` with your chosen absolute container working directory
before running Compose; it supplies both the build argument and volume targets.
For a direct Docker build, pass `--build-arg MATHFORMER_CONTAINER_ROOT="$MATHFORMER_CONTAINER_ROOT"`.
The systemd example is a user service and expects a checkout at `%h/mathformer`;
adjust that home-relative location when installing it.

- `Dockerfile`
- `docker-compose.example.yml`
- `mathformer-mcp.service.example`

## Concurrency And Resource Limits

Every `--transport stdio` client gets its own dedicated server process — most
MCP clients spawn one `scripts/mcp_server.py` per connection, so there is no
shared Python state between them. Verified directly: five concurrent stdio
clients each spawning their own server process and calling
`mathformer_run_action` complete independently with no shared state. A
`--transport streamable-http` deployment is different: one process serves
every connected client, so concurrent tool calls run inside the same Python
process (FastMCP dispatches them concurrently rather than queuing them).

`_REGISTRY` and `_EXEC_REGISTRY` are built once at startup and never mutated
afterward, so reading them concurrently (`mathformer_list_actions`,
`mathformer_show_action`, NL routing in `mathformer_ask`) is safe with no
locking needed. The actual risk is at the filesystem level: if two concurrent
calls run the same action id, and that action's command writes to a shared
path (most `writes_artifacts` actions write a single non-unique report file
under `artifacts/`, e.g. `test:quick` writing
`artifacts/test_program/deterministic_tests.json`), their writes can
interleave. This is not new risk introduced by the MCP layer — two concurrent
`python3 scripts/mathformer.py run test:quick` CLI invocations on the same
checkout race on exactly the same file today. No per-action-id lock has been
added here, because a lock scoped to one `mcp_server.py` process would not
protect against the same race from a concurrent CLI invocation, and would
give a false sense of safety. If you run a shared `streamable-http`
deployment where multiple clients might call the same write-heavy action
concurrently, serialize those calls at the client/orchestration layer instead
of relying on the server to do it.

Every leaf action that declared no `timeout_seconds` in
`scripts/mathformer.py`'s registry (roughly 49 of them, including `mcp:serve`
itself) is capped at `_DEFAULT_TIMEOUT_SECONDS` (600 seconds) inside
`_EXEC_REGISTRY`, the registry actually used to execute calls. This is purely
an MCP-side safety net: `mathformer_list_actions`/`mathformer_show_action`/the
`mathformer://actions` resource still report the true upstream
`timeout_seconds` (including `None`) so discoverability matches the CLI
exactly — only execution is capped.

## Verifying The Server

```bash
.venv/bin/python -c "
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command='.venv/bin/python', args=['scripts/mcp_server.py'])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

asyncio.run(main())
"
```

This should print the nine tool names listed above.

## Testing

The manual snippet above is also a deterministic, automated check:
`tests/mcp/run_mcp_server_self_test.py` boots the real server subprocess over
real stdio and a real `ClientSession`, asserting the tool/resource lists,
that `mathformer_ask`/`mathformer_run_action`/`mathformer_show_action` match
the equivalent CLI invocation, that mutating actions are blocked without
`allow_mutating`, and that discoverability reports the true (uncapped)
`timeout_seconds` even though execution caps it (see Concurrency And Resource
Limits above). `tests/mcp/run_mcp_auth_adversarial_test.py` separately boots
the server with `--transport streamable-http --auth-token`, and asserts a
request with no token and a request with the wrong token are both rejected
with `401` while the correct token passes the gate.

Both are registered under the `mcp` module family in
`tests/test_program/run_comprehensive_tests.py` (skipped, not failed, when
the optional `mcp` dependency is not installed) and run as part of the quick
tier:

```bash
python3 tests/test_program/run_comprehensive_tests.py --module-family mcp --json
python3 tests/run_quick.py
```

Run a script directly while iterating on `scripts/mcp_server.py`:

```bash
.venv/bin/python tests/mcp/run_mcp_server_self_test.py
.venv/bin/python tests/mcp/run_mcp_auth_adversarial_test.py
```

A meta-check inside the self-test (`tools.cli_sync`) compares the CLI's
subcommand set against `EXPECTED_TOOL_TO_SUBCOMMAND`'s values, so adding or
removing a `scripts/mathformer.py` subcommand without updating
`scripts/mcp_server.py` to match fails the test loudly instead of silently
drifting.

## Troubleshooting

- `ModuleNotFoundError: No module named 'mcp'`: run
  `uv run python scripts/install_env.py --with-mcp`, then point the client at
  `.venv/bin/python`, not a system Python.
- A mutating tool call returns `preflight_errors` instead of running: this is
  expected. Pass `allow_mutating=True` once you intend the write, or
  `dry_run=True` to see the resolved command first.
- The client shows the server as connected but with no tools: confirm the
  client's working directory is the repository root, since `mcp_server.py`
  resolves repository-relative paths from `scripts/mathformer.py`'s
  `REPO_ROOT`.

## Normalized workflow discovery

The complete `workflow-skill/v1` registry is available through
`mathformer_list_workflows(category?, query?, offset=0, limit=50)` and
`mathformer_show_workflow(workflow_id)`. List responses include total counts and
`next_offset`; IDs and explicit native aliases are accepted for inspection.
Contracts include their source links, coverage and qualification gaps.

`mathformer_run_workflow(workflow_id, dry_run=false, allow_mutating=false,
keep_going=false, extra_args?)` dispatches canonical hub/route identities through
the same controlled native execution as existing MCP tools. It retains timeout
caps, mutation preflight, configured service read-only behavior and write-root
checks. Declarative loop/profile contracts return `specification_only` and never
execute generated or arbitrary YAML instructions. Extra arguments are accepted
only for native hub actions that permit them.

Resources are `mathformer://workflows` (full catalog),
`mathformer://workflows/{workflow_id}` (full contract) and
`mathformer://workflow-schema` (shared JSON Schema). The independent service's
coverage report includes the same catalog counts and tool names. Existing server
processes must restart to load updated tool definitions; provider credentials
remain configured under `config/`.

## AgentC refinement step tools

The `loop_draft_execute_refine_loop_workflow` contract binds five MCP tools:
`mathformer_agentc_initialize_and_assess`, `mathformer_agentc_compute_iteration_guard`,
`mathformer_agentc_record_early_stop`, `mathformer_agentc_formal_repair_round`, and
`mathformer_agentc_semantic_repair_round`. These execute the same native step
iterator consumed by `IterativeSelfRefinementAgentC.run`; JSON state and history
cross each tool boundary. Early stop retains its statement/context taxonomy inputs.

The authored contract is `skills/autoformalization/autoformalization-agentc/workflow.yaml`.
The native normalizer projects it into the normalized catalog instead of replacing
it with a declarative placeholder. Completion at the default cap of four returns
candidate history even when compilation or semantic critique still fails.
Completion does not establish scientific acceptance or promote an artifact.

For real generation, launch the service with its config file and set
`providers.default_llm_provider = "openai"`, `providers.default_llm_model`,
`external_api_keys.openai_api_key`, and `lean.workdir` (an existing Lake project).
The provider adapter uses the [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses#2-map-messages-to-items)
with the native AgentC messages. It has no default model or credential fallback.
The service read-only policy and configured artifact write roots remain enforced;
provider requests and Lean compilation use configured timeouts. Compilation files
and error logs are kept in separate directories under `artifacts/agentc_steps`.

Provider-free tests use deterministic model/compiler seams:

```sh
python -m pytest -q tests/mcp/test_agentc_workflow_tools.py
```

For the cross-repository MCP/Lunar execution check, run from Lunar:

```sh
MATHFORMER_TEST_ROOT=inputs/mathformer PYTHONPATH=app/backend \
  python -m pytest -q app/backend/tests/test_mathformer_agentc_integration.py
```

The test server substitutes providers only inside the fixture process; the
production tools have no mock-provider switch. No API key or Lean installation
is needed for these tests.
