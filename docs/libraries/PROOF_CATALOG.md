<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Give readers one compact catalog of the proof-oriented Lean artifacts
  documented under the Mathformer library documentation surface.

Intent:
  Link each proof family to the generated Markdown page that contains
  declaration-level descriptions, source lines, generated notes, and Lean
  excerpts.

Function:
  Summarizes accepted and candidate libraries/MathformerLib/Mathformer theorem modules
  by mathematical topic, proof count, status, and documentation target.

Maintenance Notes:
  Keep this catalog aligned with docs/libraries/mathformerlib/modules whenever generated
  Lean documentation is refreshed or new MathformerLib proof modules are
  promoted.
-->

# Proof Catalog

This catalog points to the generated Markdown descriptions for the proof
artifacts currently surfaced through the Mathformer library documentation.
Those module pages contain the detailed proof descriptions: declaration names,
generated notes, Lean source excerpts, source-line links, imports, hashes, and
status labels.

Current catalog scope:

- Module pages: `15`
- Theorem/lemma declarations: `145`
- Accepted library module pages: `1`
- Candidate proof-module pages: `14`

Status labels matter. `accepted` means the module has been promoted into the
reusable MathformerLib surface. `candidate` means the module is documented and
inspectable, but should still be read as an autoformalization candidate unless
the surrounding validation report promotes it.

## Catalog

| Proof Family | Description | Proofs | Status | Documentation |
| --- | --- | ---: | --- | --- |
| MathformerLib root smoke proof | Minimal accepted theorem proving that the reusable library root builds. | 1 | `accepted` | [MathformerLib.Basic](mathformerlib/modules/MathformerLib/Basic.md) |
| Mathformer root module | Minimal root module for the broader Mathformer namespace. Included for catalog completeness; it has no theorem/lemma declarations. | 0 | `candidate` | [Mathformer.Basic](mathformerlib/modules/Mathformer/Basic.md) |
| Cantor-Bernstein theory, Chapter 1 | Countability foundations: denumerability, countable unions, powerset non-enumerability, finite descending chains, and Cantor-Bernstein components. | 17 | `candidate` | [AutoformalizedCBTChapter1](mathformerlib/modules/Mathformer/AutoformalizedCBTChapter1.md) |
| Cantor-Bernstein theory, Chapter 2 | Same-power relation laws, cardinal comparison scaffolding, aleph-scale style structures, union theorems, sum lemmas, and sequent lemmas. | 25 | `candidate` | [AutoformalizedCBTChapter2](mathformerlib/modules/Mathformer/AutoformalizedCBTChapter2.md) |
| Cantor-Bernstein theory, Chapter 3 | Power classes, embeddings, sandwich and antisymmetry arguments, single-set and two-set Cantor-Bernstein forms, continuum frames, and higher-cardinality comparisons. | 21 | `candidate` | [AutoformalizedCBTChapter3](mathformerlib/modules/Mathformer/AutoformalizedCBTChapter3.md) |
| Choquet theory | Convex compact-set interfaces, extreme-point support, Krein-Milman/Choquet representation statements, barycenter formulas, and simplex uniqueness statements. | 13 | `candidate` | [AutoformalizedChoquetTheory](mathformerlib/modules/Mathformer/AutoformalizedChoquetTheory.md) |
| Small examples | Compact examples including addition commutativity, Euler-formula style structure, projection measurability, and Cramer-Wold style claims. | 6 | `candidate` | [AutoformalizedExamples](mathformerlib/modules/Mathformer/AutoformalizedExamples.md) |
| Growth functions | Concept-class traces, finite trace bounds, growth-function upper and lower bounds, and shattering-to-growth statements. | 9 | `candidate` | [AutoformalizedGrowthFunction](mathformerlib/modules/Mathformer/AutoformalizedGrowthFunction.md) |
| Helly theorem | Finite, compact, set-family, and Euclidean variants of Helly-style intersection theorems. | 12 | `candidate` | [AutoformalizedHellysTheorem](mathformerlib/modules/Mathformer/AutoformalizedHellysTheorem.md) |
| Hille-Yosida theorem | C0-semigroup accessors, resolvent and generator interface lemmas, bounded-generation statements, and general/contraction Hille-Yosida theorem surfaces. | 10 | `candidate` | [AutoformalizedHilleYosida](mathformerlib/modules/Mathformer/AutoformalizedHilleYosida.md) |
| Radon's theorem | Affine-dependence lemmas, Radon partition existence, point-level partition variants, and Euclidean finite-dimensional forms. | 7 | `candidate` | [AutoformalizedRadonsTheorem](mathformerlib/modules/Mathformer/AutoformalizedRadonsTheorem.md) |
| Representer theorem | Kernel-combination evaluation, training-value equivalence, minimizer-to-representer reduction, and real-valued representer theorem surface. | 4 | `candidate` | [AutoformalizedRepresenterTheorem](mathformerlib/modules/Mathformer/AutoformalizedRepresenterTheorem.md) |
| Sazonov theorem | Hilbert-Schmidt interface lemmas, gamma-radonifying comparison statements, and a Sazonov-style equivalence. | 6 | `candidate` | [AutoformalizedSazonov](mathformerlib/modules/Mathformer/AutoformalizedSazonov.md) |
| Transformer scaling laws | Power-law positivity, Lipschitz data scaling, transformer approximation, and model/data scaling-law theorem surfaces. | 7 | `candidate` | [AutoformalizedTransformerScalingLaws](mathformerlib/modules/Mathformer/AutoformalizedTransformerScalingLaws.md) |
| VC dimension | Trace membership, powerset trace bounds, shattering equivalences, monotonicity, finite VC-dimension witnesses, and empty-set shattering. | 7 | `candidate` | [AutoformalizedVCDimension](mathformerlib/modules/Mathformer/AutoformalizedVCDimension.md) |

## Generated Library Indexes

- [Mathformer library Markdown index](mathformerlib/INDEX.md)
- [Aligned HTML index](mathformerlib/aligned/INDEX.html)
- [SymPy documentation index](mathformerlib/sympy/INDEX.md)
- [Physics SymPy documentation index](mathformerlib/sympy/physics/INDEX.md)

## Reading A Proof Page

Each linked module page is organized around declarations. For each theorem or
lemma, inspect:

- the source line link back to the Lean file;
- the generated natural-language note;
- the generated LaTeX when available;
- the Lean declaration body;
- the module imports and status metadata.

The catalog is an orientation layer. The linked module pages remain the detailed
proof descriptions.
