<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

Intent:
  Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.

Function:
  Contains executable tests, fixtures, and manifests used for local and CI validation.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Controlled Wikipedia-Level LaTeX-to-Lean Cases

This suite contains synthetic, controlled proof cases written in a compact
Wikipedia-style exposition. They are not copied from Wikipedia; they are meant
to exercise the pipeline on familiar statements with explicit bindings,
complete proof steps, and mathlib-friendly Lean targets.

Each case includes:

- a theorem statement and proof in LaTeX;
- metadata comments with a stable case id and expected Lean theorem name;
- an explicit "Lean target" paragraph describing the intended formal shape.

The corresponding Lean gold targets live in `tests/lean/WikiLevelGold.lean`.
The manifest in `manifest.json` connects each LaTeX file to its Lean theorem,
concept tags, expected imports, and the pipeline checks it is intended to
exercise.

Run the deterministic calibration pass from the repository root with:

```bash
python3 tests/wiki_level/run_suite.py
```

The runner writes:

- `artifacts/wiki_level_suite/report.json`
- `artifacts/wiki_level_suite/reasoning.jsonl`
- `artifacts/wiki_level_suite/compatibility_audit.json`

The pass covers static LaTeX metadata/binding checks, proof-expansion
difficulty estimation, concept-to-mathlib mapping with verified candidates,
mathlib hierarchy navigation, expected declaration `#check`s, Lean execution,
and the mathlib compatibility audit.
