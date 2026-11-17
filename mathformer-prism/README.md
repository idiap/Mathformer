<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Mathformer PRISM workflows

This directory was rebuilt from the canonical Mathformer loop contracts using the updated `to_prism` package.

- Public entrypoints: 14 named workflows under `projects/<workflow>/prism_project/main.prism`.
- Domain modules retain the original workflow name (`<workflow>.prism`); reasoning imports occurrences and relations as modules instead of enumerating their exports.
- Every public entrypoint is a reviewed human-scale generative reasoning projection; its detailed hook pipeline remains available as `material_main.prism`.
- Projection skill mappings provide reviewed generative context and do not claim that deterministic material checks ran inside the reasoning agent.
- Canonical skills: preserved in `../skills`; no skill-level PRISM entrypoints are published.
- Provenance: deterministic material bindings return `Computed[T]`; genuine model-dependent occurrences return `Generated[T]`.
- Output class: linked development projects. Set `PRISM_BIN` to the pinned PRISM executable before running a project launcher.
- Evidence cap: fake-handler runs establish typed topology and trace smoke only, not native, behavioral, semantic, or epistemic equivalence.

The aggregate catalog is `workflow_catalog.json`; each project contains its reviewed linked-workflow architecture plan, semantic taxonomy, hook coverage, and generated-source hashes. These linked plans are not `to_prism` executable generation plans because unadapted native operations are retained as explicit non-executing descriptors rather than falsely presented as Python-backed computation.

## End-to-end verification

The default parallel check uses the deterministic fake handler. It runs all 14 public reasoning entrypoints and their detailed material entrypoints with up to four concurrent workflows:

```bash
uv run python scripts/prism/verify_mathformer_prism.py \
  --root mathformer-prism \
  --jobs 4 \
  --handler fake \
  --output mathformer-prism/tests/parallel-workflow-conformance.json
```

That report establishes schema, nominal type-chain, reasoning/material layer, skill-binding, hook-coverage, offline-verification, negative-control, and process-overlap conformance. Fake traces are smoke evidence: they do not establish provider-native execution, behavioral correspondence, or semantic correctness.

The comprehensive test matrix also registers a bounded native Codex pilot for `reflection_testing_loop`:

```bash
uv run python scripts/prism/verify_mathformer_prism.py \
  --root mathformer-prism \
  --jobs 1 \
  --handler codex \
  --workflow reflection_testing_loop \
  --output artifacts/test_program/prism-native-reflection-testing-loop.json
```

The pilot invokes four public reasoning occurrences and the one epistemic occurrence in the detailed material workflow. It requires accepted, non-synthetic Codex effect records, correct terminal nominal types, and conservative handling of the repository's explicit placeholder fixture: the result must carry a non-success disposition plus blockers or limitations. It therefore establishes provider-native execution and placeholder-evidence safety for this workflow and fixture. It does not establish domain truth, performance, reproducibility across model versions, or equivalence between the intentionally distinct reasoning and material contracts. The matrix marks `codex` as optional, so environments without the Codex executable skip this cost-bearing check unless warnings are promoted to failures.

To execute the same bounded semantic oracle across all 14 workflows, run:

```bash
uv run python scripts/prism/verify_mathformer_prism.py \
  --root mathformer-prism \
  --jobs 4 \
  --handler codex \
  --output mathformer-prism/tests/native-semantic-parallel-e2e.json
```

The full command performs 106 public reasoning and 56 detailed-material native model occurrences. Its parallelism is capped at four workflows. Passing expands the native and placeholder-safety evidence to every catalog workflow, but retains the same semantic boundary: it is a safety oracle over generated placeholder inputs, not a proof that workflow conclusions are true or equivalent.

Source fingerprint: `sha256:3884be8eafb4f914053ef1bdcfa1689be769e9a8ac43dd3e19c6454031d2580f`.
