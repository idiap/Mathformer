<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

# Dependencies

Direct third-party code used at runtime or included in the distribution. Transitive and development-only dependencies are excluded.

This direct-only inventory covers all five Python runtime profiles in
`pyproject.toml` (`physics`, `mcp`, `documents`, `providers`, and
`knowledge-base`), the independent MCP service in `requirements-mcp-service.txt`,
and Starlette, which the MCP server imports directly. It also covers Python,
Lean 4 (including its Lake executable), the directly required mathlib4 library,
optional external IsarMathLib, external proof engines and the Codex CLI invoked
by autoformalization/judge workflows, and browser libraries directly loaded by
generated reports and workflow pages.

`uv.lock` supplies release references for the direct Python packages; its
transitive dependency tree is excluded. The other libraries in
`lake-manifest.json` are indirect mathlib dependencies and are excluded.
Environment managers, build/export orchestration, validators, tests, linters,
documentation tools, and their exclusive dependencies are outside the runtime
scope. This is not a complete transitive or binary component inventory.
Bundled-component qualifications and upstream notice obligations still apply to
the parent dependencies; nested components are not separate rows.

External Isabelle, Rocq, Vampire, and Codex releases are not pinned here. Their
rows identify upstream core terms; exact binary bundles retain their own
component notices. MathJax is loaded with a floating major-version URL (`@3`);
the linked license is for the 3.2.2 release. The optional PRISM/Lunar host's
release, license, and canonical upstream URL remain unresolved in this repository.
ProofWidgets' optional frontend build is not part of the tracked distribution.
Downloaded model weights, datasets, and user documents keep their own terms and
are outside this code inventory.

| Name of 3rd party code | License | Web page location |
| --- | --- | --- |
| anthropic | MIT ([0.118.0](https://pypi.org/project/anthropic/0.118.0/)) | [PyPI](https://pypi.org/project/anthropic/) |
| beautifulsoup4 | MIT ([4.15.0](https://pypi.org/project/beautifulsoup4/4.15.0/)) | [PyPI](https://pypi.org/project/beautifulsoup4/) |
| Codex CLI | [Apache-2.0](https://github.com/openai/codex/blob/main/LICENSE); bundled-component notices also apply | [Codex](https://github.com/openai/codex) |
| Cytoscape.js | [MIT](https://github.com/cytoscape/cytoscape.js/blob/v3.28.1/LICENSE) | [Cytoscape.js](https://github.com/cytoscape/cytoscape.js) |
| docling | MIT ([2.114.0](https://pypi.org/project/docling/2.114.0/)) | [PyPI](https://pypi.org/project/docling/) |
| google-genai | Apache-2.0 ([1.75.0](https://pypi.org/project/google-genai/1.75.0/)) | [PyPI](https://pypi.org/project/google-genai/) |
| highlight.js | BSD-3-Clause ([11.9.0](https://github.com/highlightjs/highlight.js/blob/11.9.0/LICENSE); [11.11.1](https://github.com/highlightjs/highlight.js/blob/11.11.1/LICENSE)) | [highlight.js](https://github.com/highlightjs/highlight.js) |
| httpx | BSD-3-Clause ([0.28.1](https://pypi.org/project/httpx/0.28.1/)) | [PyPI](https://pypi.org/project/httpx/) |
| huggingface-hub | Apache-2.0 ([0.36.2](https://pypi.org/project/huggingface-hub/0.36.2/)) | [PyPI](https://pypi.org/project/huggingface-hub/) |
| Isabelle | [BSD-style core; bundled components have separate licenses](https://isabelle.in.tum.de/index.html) | [Isabelle](https://isabelle.in.tum.de/) |
| IsarMathLib (optional external installation; not bundled) | [BSD-3-Clause](https://github.com/SKolodynski/IsarMathLib/blob/d1df8f2aed2e5cee934caea4a99906cdd42ac371/LICENSE) | [IsarMathLib](https://isarmathlib.org/) |
| Lean 4 | [Apache-2.0](https://github.com/leanprover/lean4/blob/v4.24.0/LICENSE) | [Lean](https://github.com/leanprover/lean4) |
| MathJax | [Apache-2.0](https://github.com/mathjax/MathJax/blob/3.2.2/LICENSE) | [MathJax](https://github.com/mathjax/MathJax) |
| mathlib4 | [Apache-2.0](https://github.com/leanprover-community/mathlib4/blob/f897ebcf72cd16f89ab4577d0c826cd14afaafc7/LICENSE) | [mathlib4](https://github.com/leanprover-community/mathlib4) |
| matplotlib | Matplotlib License (PSF-based); bundled font and library licenses, including OFL-1.1, Apache-2.0, MIT, Qhull, and custom font terms ([3.11.1](https://pypi.org/project/matplotlib/3.11.1/)) | [PyPI](https://pypi.org/project/matplotlib/) |
| mcp | MIT ([1.28.1](https://pypi.org/project/mcp/1.28.1/)) | [PyPI](https://pypi.org/project/mcp/) |
| numpy | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 ([release 2.4.6](https://pypi.org/project/numpy/2.4.6/); [release 2.5.1](https://pypi.org/project/numpy/2.5.1/)) | [PyPI](https://pypi.org/project/numpy/) |
| openai | Apache-2.0 ([2.47.0](https://pypi.org/project/openai/2.47.0/)) | [PyPI](https://pypi.org/project/openai/) |
| PRISM / Lunar runtime (optional external host) | Unresolved — host release and applicable license are not declared in this repository | Unresolved — no upstream host URL is declared |
| Python | [PSF-2.0 and historical component licenses](https://docs.python.org/3/license.html) | [Python](https://www.python.org/) |
| Rocq Prover / Coq | [GNU LGPL 2.1](https://github.com/rocq-prover/rocq/blob/master/LICENSE) | [Rocq](https://rocq-prover.org/) |
| starlette | BSD-3-Clause ([1.3.1](https://pypi.org/project/starlette/1.3.1/)) | [PyPI](https://pypi.org/project/starlette/) |
| sympy | BSD-3-Clause AND MIT (bundled LaTeX parser) ([1.14.0](https://pypi.org/project/sympy/1.14.0/)) | [PyPI](https://pypi.org/project/sympy/) |
| uvicorn | BSD-3-Clause ([0.51.0](https://pypi.org/project/uvicorn/0.51.0/)) | [PyPI](https://pypi.org/project/uvicorn/) |
| Vampire | [Vampire BSD 3-Clause license; bundled components have separate licenses](https://github.com/vprover/vampire/blob/master/LICENCE) | [Vampire](https://github.com/vprover/vampire) |
