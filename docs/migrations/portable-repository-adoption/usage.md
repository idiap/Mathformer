<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Use the portable adoption pilot

Existing commands and canonical skill locations remain the public interfaces.
The new hub actions offer explicit discovery, validation and recorded invocations
for the [frozen pilot](scope-map.md). No imported example code is installed.

## Software release archives

The historical `evidence/` directory contains machine-specific paths and immutable
receipts with content digests. Its original bytes remain in Git for provenance;
`.gitattributes` excludes the directory from `git archive` releases. Links to
historical evidence in these migration documents therefore require a repository
checkout. The local `paper/` directory is ignored by Git and explicitly excluded
from archives as well.

After committing release changes, build the source release with:

```bash
git archive --format=tar.gz --output=../mathformer-source.tar.gz HEAD
```

Any alternative release packager must apply the same exclusions. A Git clone
still contains historical evidence; these archive rules do not sanitize Git
history or a checkout. Licensing metadata is maintained in the root `REUSE.toml`.

## Run the pilot

From the repository root, validate the pilot through natural language:

```bash
python3 scripts/mathformer.py ask "validate portable repository adoption" --run --json
```

Inspect [generated operation discovery](catalog.md) or resolve an alias:

```bash
python3 scripts/mathformer.py run adoption:describe --json -- workflow-contract-validator:validate
```

Run the existing contract validator with a new immutable receipt directory:

```bash
python3 scripts/mathformer.py run adoption:invoke --json -- control:workflow-contract
```

Receipts appear under `artifacts/adoption/<invocation-id>/`: `result.json` is the
exact JSON snapshot, `reasoning.jsonl` uses the existing logger, and
`provenance.json` joins invocation, metadata and result digests. CLI output keeps
the new adapter's result separate from the legacy command. The validator adapter
returns the existing hub execution report, including the legacy stdout and exit
status. Check those fields to distinguish an operation that completed with
findings from a successful validation assessment.

The new router adapter returns JSON route candidates without executing them:

```bash
python3 scripts/mathformer.py run adoption:invoke --json -- router:resolve --inputs '{"request":"make sure every workflow is controlled"}'
```

`control:reasoning-log-summary` and `reasoning-log:validate` accept
`--inputs '{"log_file":"path/to/public-log.jsonl"}'`. Only record logs and results
appropriate for public evidence. The generic recorder has no reliable way to
classify arbitrary content as safe; input arguments, environment and exception
messages are omitted, but a caller's result may itself contain sensitive text.
Legacy append and HTML operations remain discoverable through their native
bindings and are not given a second write adapter.

Offline validation and rendering never invoke an operation. Replace
`<invocation-id>` below with the directory name produced by the invocation:

```bash
python3 scripts/mathformer.py run adoption:receipt-validate --json -- artifacts/adoption/<invocation-id>
python3 scripts/mathformer.py run adoption:receipt-render --json -- artifacts/adoption/<invocation-id>
```

The render action returns escaped HTML through the hub's stdout field. It does
not execute generation or modify the receipt. For a standalone HTML file, the
underlying documented module can be used after selecting the hub action:

```bash
python3 skills/control/reasoning-log-schema-guardian/scripts/adoption_provenance.py render artifacts/adoption/<invocation-id> > artifacts/adoption-receipt.html
```

The two PRISM adapters are deliberately fixture-only:

```bash
python3 scripts/mathformer.py run adoption:invoke --json -- artifact_acceptance_loop:public
python3 scripts/mathformer.py run adoption:invoke --json -- artifact_acceptance_loop:material
```

They use the existing adjacent `to_prism/.venv/bin/prism`, explicitly choose the
fake handler, run the existing project entrypoint in its original directory,
and verify the trace offline using temporary output files. A receipt carries
`fixture: true`, `handler: fake` and `backend_verified: false`. This proves neither
native-provider behavior nor that a Lean artifact was checked. The material
fixture explicitly reports that native implementation was not executed.

Regenerate the catalog after editing canonical metadata, then check drift:

```bash
python3 scripts/mathformer.py run adoption:catalog --allow-mutating --json
python3 scripts/mathformer.py run adoption:catalog-check --json
```

Only the explicit generator writes the catalog. Its output is derived from the
canonical contract; it is not another authored registry. Existing agent host
projections continue resolving the same canonical skill directories. The
[contract](contracts.md) describes optional recording failure, exact serialization
and boundaries such as synchronous execution and caller-owned retries.
