<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make the framework understandable without requiring readers to inspect implementation details first.

Intent:
  Explain architecture, installation, principles, tutorials, licensing, and generated library outputs.

Function:
  Provides human-facing documentation that should stay aligned with tested behavior and code paths.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Vampire ATP Interface

Mathformer can run first-order ATP proof search through Vampire using TPTP FOF
as the interchange format.

## Install

Install Vampire with the package or binary appropriate for your platform. On
macOS with Homebrew:

```bash
brew install vampire
```

Check the installed binary:

```bash
vampire --version
```

The repository code has no extra runtime dependency beyond Python's standard
library. The skill validator runs in the project `uv` environment.

If Vampire is installed outside `PATH`, set `VAMPIRE_BIN` or pass
`--vampire-bin path/to/vampire` to the CLI.

## Python Interface

Use `backends.atp.MathformerATP.vampire`:

```python
from pathlib import Path
from backends.atp.MathformerATP.vampire import VampireRunner, discover_proof

report = discover_proof(
    "If R is a subset of S and S is a subset of T, then R is a subset of T.",
    artifact_root=Path("artifacts/vampire_atp/subset_transitive_web"),
    source_url="https://proofwiki.org/wiki/Subset_Relation_is_Transitive",
)
assert report["ok"]
assert report["winning_formal_proof"]
assert report["winning_informal_proof"]["ok"]
```

Core entrypoints:

- `ATPProblem`: structured TPTP problem with informal provenance.
- `ATPResult`: Vampire result with `formal_proof` and `informal_proof`.
- `InformalProof`: Markdown-ready informalization of the formal proof result.
- `PremiseCandidate`: a candidate premise with provenance, trust state, score,
  and rejection reason.
- `PremiseSelectionReport`: selected and rejected premise candidates for a
  theorem attempt.
- `GeneratedLemma`: a generated helper lemma plus its separate proof/promotion
  state.
- `PremiseGenerationReport`: generated, proved, promoted, and rejected helper
  lemmas.
- `TPTPFormula`: one `fof`, `cnf`, or similar formula.
- `VampireRunner.run_path(path, time_limit=10)`: run a TPTP file.
- `VampireRunner.run_problem(problem, output_path=...)`: write and run a problem.
- `aggressive_autoformalize(text)`: generate built-in TPTP candidates.
- `informalize_proof(result, problem=...)`: build a readable proof explanation.
- `transitive_irreflexive_asymmetric_problem(...)`: construct a relation-theory proof.
- `unary_implication_chain_problem(...)`: construct a simple transitive predicate-chain proof.
- `discover_proof(text, artifact_root=..., premise_loop=True)`: optionally run
  premise selection, generated-lemma proof, and premise minimization before
  Vampire proof search.

## Premise Selection And Generation

Informal proof discovery can opt into a premise-guided loop with
`premise_loop=True` in Python or `--premise-loop` in the CLI:

1. Build a premise universe from the autoformalized theorem context plus a small
   local registry of relevant and distracting candidates.
2. Score candidates by trusted provenance, symbol overlap, domain overlap, and
   theorem-shape overlap.
3. Select only trusted premises: `source_assumption`, `library_fact`,
   `definition_expansion`, or already `proved_generated_lemma`.
4. Generate theorem-specific helper lemmas when a proof plan suggests useful
   intermediate facts.
5. Prove each generated lemma in a separate Vampire obligation using only the
   selected trusted premises.
6. Promote generated lemmas only after proof. Unproved or unsafe generated
   premises remain visible in reports but are not inserted into theorem attempts.
7. Minimize the final successful premise set by removing premises one at a time
   and re-running Vampire.

For the group inverse-of-product example, the system selects the five group
axioms from the source context, proves three generated helper lemmas, rejects an
unsafe commutativity shortcut, then proves the target theorem from the minimized
set of proved generated lemmas:

- `generated_product_candidate_right_inverse`
- `generated_product_candidate_left_inverse`
- `generated_two_sided_inverse_unique`

For the triple-product example, the system proves and promotes the binary
inverse-of-product lemma, then proves:

```text
inv(mul(mul(x,y),z)) = mul(inv(z),mul(inv(y),inv(x)))
```

Each premise-guided run writes:

- `premise_selection_report.json`
- `premise_generation_report.json`
- `premise_minimization_report.json`

The top-level `discovery_report.json` also includes the winning report paths and
`winning_final_premise_ids`.

## CLI

Run a TPTP file:

```bash
python scripts/run_vampire_atp.py --problem path/to/problem.p --json
```

Autoformalize and prove the representative informal example:

```bash
python scripts/run_vampire_atp.py \
  --text-file tests/atp/informal_subset_transitive.md \
  --source-url https://proofwiki.org/wiki/Subset_Relation_is_Transitive \
  --artifact-root artifacts/vampire_atp/subset_transitive_cli \
  --json
```

Useful premise-loop controls:

```bash
python scripts/run_vampire_atp.py \
  --text-file examples/vampire_group_inverse_product_input.md \
  --artifact-root artifacts/vampire_atp/group_inverse_product_cli \
  --premise-loop \
  --premise-budget medium
```

Plain discovery is the legacy direct template-to-Vampire path. Use
`--premise-loop` for premise selection/generation, `--no-premise-generation` to
disable generated helper lemmas once the loop is enabled, and
`--no-premise-minimization` to keep the selected/promoted premise set unchanged.

Run the regression:

```bash
python tests/atp/run_vampire_interface.py --json
python tests/atp/run_premise_guided_group_inverse.py --json
python tests/atp/run_premise_guided_triple_inverse.py --json
```

## Realistic Informal Input Example

Run a plain-English compliance-chain example:

```bash
python examples/vampire_informal_to_proofs.py
```

Input:

```text
Every audited invoice is a compliant invoice. Every compliant invoice is a payable invoice.
Therefore every audited invoice is a payable invoice.
```

The example writes:

- `artifacts/vampire_atp/policy_chain_example/candidate_01_unary_implication_chain_audited_invoice_to_payable_invoice.p`
- `artifacts/vampire_atp/policy_chain_example/candidate_01_unary_implication_chain_audited_invoice_to_payable_invoice.proof.tstp`
- `artifacts/vampire_atp/policy_chain_example/candidate_01_unary_implication_chain_audited_invoice_to_payable_invoice.informal.md`
- `artifacts/vampire_atp/policy_chain_example/discovery_report.json`

## Nontrivial Mathematical Example

Run the relation-theory example:

```bash
python examples/vampire_nontrivial_math_to_proofs.py
```

Input:

```text
Let r be a binary relation. Assume r is transitive: whenever r(x,y) and r(y,z), r(x,z).
Assume r is irreflexive: r(x,x) never holds.
Prove that r is asymmetric: if r(x,y), then not r(y,x).
```

The autoformalized TPTP problem encodes:

- transitivity: `r(X,Y) ∧ r(Y,Z) -> r(X,Z)`
- irreflexivity: `not r(X,X)`
- conjecture: `r(X,Y) -> not r(Y,X)`

The proof uses contradiction: if both `r(x,y)` and `r(y,x)` held, transitivity
would give `r(x,x)`, contradicting irreflexivity.

## Complex Equational Group Example

Run the group-theory example:

```bash
python examples/vampire_complex_group_theorem_to_proofs.py
```

Input:

```text
Let G be a group with multiplication mul, identity element e, and inverse operation inv.
Prove that for all elements x and y of G, the inverse of the product mul(x,y)
is the product of the inverses in reverse order: inv(mul(x,y)) = mul(inv(y),inv(x)).
```

The autoformalized TPTP problem uses equality and group axioms:

- associativity of `mul`
- left and right identity laws for `e`
- left and right inverse laws for `inv`
- conjecture: `inv(mul(X,Y)) = mul(inv(Y),inv(X))`

This is a more complex ATP use case because Vampire must reason equationally
with associativity, identity simplification, inverse laws, and a negated
universal equality conjecture.

Expected result:

- `ok: true`
- `winning_status: Theorem`
- a generated `.p` file
- a Vampire result JSON file
- a non-empty `.proof.tstp` formal proof file
- a `.informal.md` readable proof explanation
- a `.informal.json` structured informal proof payload
- `premise_selection_report.json`
- `premise_generation_report.json`
- `premise_minimization_report.json`

`discover_proof(...)` also returns `winning_formal_proof`,
`winning_informal_proof`, `winning_formal_proof_path`, and
`winning_informal_proof_path`, plus the winning premise report paths and
`winning_final_premise_ids` in the discovery report.
