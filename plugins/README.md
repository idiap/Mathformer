<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Mathformer agent plugin

`plugins/mathformer/` is one repository-backed plugin for Codex and Claude
Code. Both clients discover the same skills through flat
`skills/<skill-name>/SKILL.md` entrypoints. The authored implementations remain
in the repository's thematic `skills/<theme>/<skill-name>/` directories.

```text
.agents/plugins/marketplace.json       Codex marketplace
.claude-plugin/marketplace.json        Claude marketplace
plugins/mathformer/
  .codex-plugin/plugin.json            Codex compatibility manifest
  .claude-plugin/plugin.json           Claude manifest
  skills/<skill-name>/SKILL.md         Generated discovery entrypoints
  skills/<workflow-name>/workflow.yaml Normalized workflow contracts
  workflow-catalog.json               Canonical ID to client-name mapping
  workflow.schema.json                Shared contract schema
  hub-interface.schema.json           Native hub payload schemas
  LICENSE
```

## Runtime checkout

Install the plugin and keep a local Mathformer checkout with the environment
and backends needed for your work. Start your agent in that checkout, or set
`MATHFORMER_ROOT` to its absolute path before starting the client. An agent
started below the checkout root can find it through parent directories.
The entrypoints load the canonical instructions and resolve resources there.
If no checkout can be found, the agent requests its path.

The plugin cache contains discovery instructions; it does not contain the
Mathformer runtime, backend binaries, environments, credentials, or generated
proofs. Installing it does not install those dependencies or configure the
Mathformer MCP service. Follow the [environment guide](../docs/getting-started/INSTALL.md)
and [service configuration guide](../config/README.md) when needed.

All normalized workflows are published as additional flat skill entrypoints,
with their full YAML contracts and local schemas. `workflow-catalog.json` maps
canonical `_workflow` IDs to portable client names; names longer than 64
characters use a stable suffix. Both clients read the same generated catalog.
The existing runtime skill entrypoints remain available alongside these workflow
entrypoints. Loop and semantic-profile contracts expose their participants and
gaps for inspection and do not claim an executable normalized implementation.

When the MCP service is configured, use `mathformer_list_workflows` to list/filter
the same catalog, `mathformer_show_workflow` for a full contract, and
`mathformer_run_workflow` for native hub/route execution. Native permissions,
service write roots and backend gates still apply.

## Codex installation

From the repository root:

```bash
codex plugin marketplace add .
```

In the ChatGPT desktop app's Plugins Directory, select **Mathformer plugins**
and install **Mathformer**, then start a new conversation in the checkout.
CLI versions that provide `codex plugin add` can install with:

```bash
codex plugin add mathformer@mathformer-plugins
```

Ask: "Use Mathformer to validate the ATP proof-search family."
The checked-in repo marketplace makes the plugin discoverable; each client
still needs installation/enabling. No user configuration is changed by this
repository's generator.

## Claude Code installation

From the repository root:

```bash
claude plugin marketplace add .
claude plugin install mathformer@mathformer-plugins
```

Start a new session in the checkout and ask for a mathematical outcome, or use
the namespaced skill command:

```text
/mathformer:mathformer-generative-workflow-coordinator
```

For development without installation:

```bash
claude --plugin-dir ./plugins/mathformer
```

After committing and pushing the packaging, teammates with repository access
can use `git@gitlab.idiap.ch:neurosymbolicai/mathformer.git` as the marketplace
source instead of `.` in either client's marketplace-add command. They still
need a runtime checkout.

## Maintenance and validation

After changing skill names, descriptions, normalized workflow contracts, or the project version:

```bash
python scripts/mathformer.py ask "regenerate agent plugins" --run --allow-mutating
python scripts/mathformer.py ask "validate agent plugins" --run --json
python scripts/mathformer.py audit --strict --json
```

The generator is `scripts/sync_agent_plugins.py`; its `--check` mode reports
drift without writing. Generated entrypoints begin with YAML frontmatter even
when canonical skills have a license comment before it. The checker requires
unique skill names and exact source parity. Tests cover description changes,
renamed skills, duplicate rejection and discovery from a copied cache layout.
The plugin version follows `pyproject.toml`; bump it before distributing an
updated release, refresh the marketplace, and reinstall/reload the plugin in
the client so its cached discovery metadata updates. Runtime instructions come
from the selected checkout, so use a matching revision for reproducibility.

With Claude Code installed, also run:

```bash
claude plugin validate ./plugins/mathformer
claude plugin validate .
```

The existing `scripts/link_agent_skills.py` remains available for repository
discovery in Codex, Claude and OpenCode. Choose either plugin installation or
direct skill publishing for each client to avoid duplicate skill discovery.
The generator does not remove existing local discovery folders.

Format references: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins),
[Claude plugin manifests](https://code.claude.com/docs/en/plugins-reference),
and [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).
