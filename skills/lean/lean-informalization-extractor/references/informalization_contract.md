<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Lean-To-Informalization Contract

The extractor must be conservative:

- A generated informal statement is a paraphrase of the Lean signature plus the
  nearest source-aware doc comment.
- A generated proof narrative is a summary of the Lean proof body, not a
  reconstruction from mathematical background knowledge.
- Original-source prose and generated notes remain separate fields.
- Missing source comments, placeholders, target axioms, and unparsed theorem
  bodies are findings, not prose gaps to smooth over.
- Proofs closed by `exact h...` should be reported as delegated to a hypothesis;
  this can be honest when the file explicitly models an external theorem or
  criterion, but it must remain visible.

Required declaration packet fields:

- `kind`, `name`, `line`, `signature`
- `doc_comment`
- `informal_statement`
- `source_alignment.original_nl`
- `source_alignment.original_latex`
- `source_alignment.generated_notes`
- `proof_summary`
- `proof_features`
- `findings`

Downstream consistency checks should treat this packet as evidence about the
Lean artifact, not as a gold reference.
