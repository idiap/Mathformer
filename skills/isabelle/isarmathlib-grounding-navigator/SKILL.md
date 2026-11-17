---
name: isarmathlib-grounding-navigator
description: Search local Isabelle/HOL and optional IsarMathLib theory trees for concepts, constants, theorem names, and likely imports before Isabelle autoformalization. Use when an Isabelle draft should be grounded in existing Isabelle sessions or IsarMathLib rather than inventing parallel definitions.
---

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

# IsarMathLib Grounding Navigator

## Purpose

Use this skill before Isabelle drafting and after source-unit extraction. It is the
Isabelle/IsarMathLib analogue of the mathlib grounding skills.

## Workflow

1. Search the requested concepts in configured theory roots.
2. Set `ISABELLE_HOME` to the Isabelle installation to include its `src/HOL` tree, or pass `--root` explicitly.
3. Search the external checkout selected by `$ISARMATHLIB_HOME`, or
   `~/.local/share/mathformer/IsarMathLib` by default. See the
   [external installation instructions](../../../docs/getting-started/INSTALL.md#external-isarmathlib).
   Mathformer does not bundle IsarMathLib sources.
4. Return candidate theory files, matching lines, and proposed imports.
5. Treat missing IsarMathLib as a nonblocking dependency gap for examples that use
   only Isabelle/HOL `Main`.
6. Do not cite a theory as authoritative unless the local file exists.
7. IsarMathLib uses Isabelle/ZF. Keep its imports within a compatible ZF session;
   do not mix them into a theory based on HOL `Main`.

## Command

```bash
python3 skills/isabelle/isarmathlib-grounding-navigator/scripts/search_isarmathlib.py \
  --concept injective --concept composition --json
```

