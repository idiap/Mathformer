---
name: reasoning-flow-language
description: Author, migrate, and validate Mathformer Epistemic Reasoning Flow Language (ERFL) 0.3 files. Use when a reasoning style or workflow must be expressed as typed epistemic occurrences, when importing an ERFL 0.2 flow, or when checking handle conservation, relation licensing, calibration, bounded iteration, alternatives, and authority-preserving terminal decisions.
---

<!--
File Documentation

Motivation:
  Make epistemic workflow composition explicit and machine-checkable without
  confusing reasoning with skill scheduling or artifact transport.

Intent:
  Give agents one compact procedure for authoring and validating ERFL 0.3
  profiles against Mathformer's reasoning and output taxonomies.

Function:
  Owns the ERFL semantic registry, deterministic validator, curated Mathformer
  reasoning-style projections, generated semantic catalogue, and separate
  operational materialization cross-reference.

Maintenance Notes:
  Keep the registry aligned with skills/REASONING_TYPES.yaml and
  skills/OUTPUT_TYPES.yaml. Never treat a valid flow as evidence that its
  scientific or mathematical goal was achieved.
-->

# Reasoning Flow Language

Use ERFL to describe epistemic dependencies among reasoning occurrences. Do
not use it as temporal telemetry or as a replacement for
`skills/SKILL_HOOKS.yaml`.

## Workflow

1. Read `references/erfl-0.3.json`, including `reference_alignment`, when
   changing symbols, relations, semantic kinds, validation rules, or the
   ERFL 0.2 adaptation boundary.
2. Start from the closest profile in `examples/reasoning_flows/`.
3. Write the program as `reasoning ID { ... }` with one `steps` expression.
   Type each occurrence as `alias:TYPE[inputs->outputs]`; add semantic port
   kinds with `handle::Kind` where authority or joins would otherwise be
   ambiguous.
4. For long expressions, put `steps` on its own line, end a continued segment
   with its explicit relation and `...`, and place the next occurrence on the
   following line. Indentation and `...` never create epistemic structure.
5. Label every transition with the relation that licenses it. Never use the
   legacy unlabelled `>` edge.
6. Bind accessible resources before the program with `@KB`, `@SEARCH`, or
   `@STORE`. Use `occurrence <-mode- resource` for consumption and only
   `calibration -mode-> resource` for persistence. Resource arrows carry no
   warrant and require runtime receipts.
7. End the steps expression, and every repeat body, in epistemic calibration `E`.
8. Keep iteration bounded and name a progress measure. Treat `_` as an
   explicit projection gap that makes the flow descriptive and non-executable.
9. Validate before publishing, comparing, or using a flow as a framework
   contract.
10. After changing a canonical profile or either registry, regenerate and check
   both `docs/architecture/ALL_REASONING_FLOWS.md` and
   `docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md`; never edit either
   generated file directly. The renderer rejects canonical skill, hook, loop,
   or action identifiers in the semantic catalogue.

## Commands

```bash
python skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py \
  examples/reasoning_flows/*.rflow \
  --strict \
  --check-registries \
  --json
```

Run the built-in positive and adversarial fixtures:

```bash
python skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py \
  --self-test \
  --json
```

Regenerate the semantic catalogue and the separate operational-materialization
cross-reference:

```bash
python skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py \
  --json
```

Check that both committed generated documents are synchronized without writing
them:

```bash
python skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py \
  --check \
  --json
```

## Interpretation Boundary

A valid ERFL file establishes only that the declared projection is
syntactically and relationally coherent under this profile. It does not show
that the projected skills ran, that the projection is complete, or that any
object-level claim is true. Bind executions separately to digested outputs,
evidence, assessments, and decisions.
