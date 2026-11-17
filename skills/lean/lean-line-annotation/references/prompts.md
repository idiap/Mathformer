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

# Lean Line Annotation Prompts

## LeanLineAnnotationAgent

### System Prompt

```text
You are an expert in Lean4 and mathematical formalization.
You will be given Lean4 source code.
Your task is to produce a line-by-line annotation of the file.
Follow these instructions exactly:
1. Output one annotation row for every input line, including blank lines.
2. Keep exact 1-based line numbers from the input.
3. Do not rewrite, reorder, or correct the Lean code.
4. Use this exact output format wrapped in fences:
%%%%%%%%%%
| line | code | annotation |
| --- | --- | --- |
| 1 | `...` | ... |
%%%%%%%%%%
5. For blank input lines, set `code` to `<blank>`.
6. Keep annotations concise and technically precise.
```

### User Prompt

```text
Lean4 source file content:
{{lean_code}}
Generate the line-by-line annotation table.
```

## Generated Lean Source Comment Guard

Use this contract when Lean code is being generated, denoised, refined, or saved
as an autoformalization artifact.

```text
Generated Lean4 source should use normal readable Lean formatting with blank lines
between coherent blocks. Source-alignment comments are required at module and
declaration level for nontrivial generated artifacts; they are not required on
every Lean line.

Allowed forms:
- a module doc comment summarizing original-source coverage, mathlib grounding,
  and generated interface boundaries;
- declaration doc comments preserving the original natural-language and LaTeX
  statement when the declaration corresponds to source material;
- declaration doc comments marked as `Generated note` / `Generated equivalent`
  when the declaration is support infrastructure introduced by formalization;
- short proof comments only before genuinely non-obvious proof blocks.

Preferred declaration comment shape:

```lean
/--
Original source (NL): Every point of a compact convex metrizable set has a representing probability measure supported on extreme points.
Original source (LaTeX): `x = \int_{\operatorname{Ext}(K)} y \, d\mu(y)`.
Mathlib grounding: The generated Lean reuses `ProbabilityMeasure`, `extremePoints`, and continuous affine maps.
-/
```

For generated declarations not present verbatim in the source:

```lean
/--
Generated note (NL): This support predicate records that a probability measure gives mass zero to the complement of a set.
Generated equivalent (LaTeX): `\operatorname{supp}(\mu) \subseteq s`, represented here as `\mu(s^c)=0`.
-/
```

Disallowed forms:
- repeated `NL/LaTeX:` comments on every Lean source line,
- comments attached to purely syntactic lines such as `import`, `open`,
  `namespace`, `section`, `end`, `set_option`, `universe`, or simple `variable`
  declarations,
- standalone separator comments such as "separates imports from declarations",
- comments that paraphrase obvious Lean syntax rather than preserving source meaning.

Before accepting generated Lean, run:

```bash
python3 skills/lean/lean-line-annotation/scripts/validate_lean_line_comments.py \
  path/to/generated.lean \
  --require-semantic-comments
```
```
