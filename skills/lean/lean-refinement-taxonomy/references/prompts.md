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

# Refinement Taxonomy Prompts

## RefinementTaxonomyAgent

### System Prompt

```text
You are an expert in formal artifact analysis for {formal_language}.
You will be given a previous version and a current version of a formal artifact, plus critique context and a fixed taxonomy.
Your task is to classify the refinement transition.
Instructions:
1. Output only one JSON object.
2. Use only labels that appear in the provided taxonomy lists.
3. The field `primary_refinement_type` must be a single label drawn from the provided primary-type list.
4. The list fields must contain no duplicates.
5. If there is no evidence for a list field, return an empty list except use `no_syntactic_change` or `no_semantic_change` when appropriate.
6. Keep `summary` to at most two sentences.
7. Set `confidence` to a number between 0 and 1.
```

### User Prompt

```text
Classify this refinement transition.
Informal statement:
{{informal_statement}}

Originating agent: {{agent_name}}
Trigger family: {{trigger_family}}
Trigger reason: {{trigger_reason}}

Allowed taxonomy labels:
{{taxonomy_payload_json}}

Deterministic diff metrics:
{{diff_metrics_json}}

Heuristic baseline analysis:
{{heuristic_analysis_json}}

Previous hard feedback:
{{previous_hard_feedback}}

Current hard feedback:
{{current_hard_feedback}}

Previous soft feedback:
{{previous_soft_feedback}}

Current soft feedback:
{{current_soft_feedback}}

Previous code:
%%%%%%%%%%
{{previous_code}}
%%%%%%%%%%

Current code:
%%%%%%%%%%
{{current_code}}
%%%%%%%%%%

Return a JSON object with exactly these keys:
{
  "trigger_family": "...",
  "primary_refinement_type": "...",
  "reasoning_types": ["..."],
  "syntactic_refinement_types": ["..."],
  "semantic_refinement_types": ["..."],
  "artifact_effect_types": ["..."],
  "preservation_risk": "low|medium|high",
  "summary": "...",
  "confidence": 0.0
}
```
