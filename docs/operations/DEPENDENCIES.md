<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Keep the project dependency surface easy to inspect before installation, release, or redistribution.

Intent:
  List Mathformer direct framework/tool dependencies and the current Python transitive inventory with names, licenses, and upstream URLs.

Function:
  Serves as a human-readable dependency index derived from docs/operations/LICENSES.md, lakefile.toml, lean-toolchain, scripts/install_env.py, and docs/operations/PYTHON_DEPENDENCY_LICENSES.md.

Maintenance Notes:
  Regenerate the Python inventory first, then refresh this index after dependency or toolchain changes. This is an engineering inventory, not legal advice.
-->

# Dependency Index

This file lists the dependency surface in the requested form: framework, dependency name, license, and upstream URL. It is an engineering inventory, not legal advice. Verify upstream license files for the exact versions and artifacts before redistribution.

## Direct Framework And Tool Dependencies

| Framework | Dependency | License | URL |
| --- | --- | --- | --- |
| Core runtime | Python | Python Software Foundation License Version 2 | <https://docs.python.org/3/license.html> |
| Python environment manager | uv | Apache-2.0 OR MIT | <https://github.com/astral-sh/uv> |
| Lean toolchain manager | elan | Apache-2.0 OR MIT | <https://github.com/leanprover/elan> |
| Lean proof assistant | Lean 4 | Apache-2.0 | <https://github.com/leanprover/lean4> |
| Lean build system | Lake | Apache-2.0 | <https://github.com/leanprover/lean4/tree/master/src/lake> |
| Lean mathematics library | mathlib4 | Apache-2.0 | <https://github.com/leanprover-community/mathlib4> |
| Lean/mathlib dependency | batteries | Apache-2.0 | <https://github.com/leanprover-community/batteries> |
| Lean/mathlib dependency | Qq | Apache-2.0 | <https://github.com/leanprover-community/quote4> |
| Lean/mathlib dependency | aesop | Apache-2.0 | <https://github.com/leanprover-community/aesop> |
| Lean/mathlib dependency | proofwidgets | Apache-2.0 | <https://github.com/leanprover-community/ProofWidgets4> |
| Lean/mathlib dependency | plausible | Apache-2.0 | <https://github.com/leanprover-community/plausible> |
| Lean/mathlib dependency | LeanSearchClient | Apache-2.0 | <https://github.com/leanprover-community/LeanSearchClient> |
| Lean/mathlib dependency | importGraph | Apache-2.0 | <https://github.com/leanprover-community/import-graph> |
| Lean/mathlib dependency | Cli / lean4-cli | MIT | <https://github.com/leanprover/lean4-cli> |
| Optional proof assistant | Rocq Prover | LGPL-2.1 for Rocq itself; preserve upstream notices for packaged distributions | <https://github.com/rocq-prover/rocq> |
| Optional proof assistant | Isabelle | BSD-style for the main codebase; application bundles include multiple licenses | <https://isabelle.in.tum.de/> |
| Optional external Isabelle/ZF library (not bundled) | IsarMathLib | BSD-3-Clause | <https://github.com/SKolodynski/IsarMathLib> |
| Optional ATP backend | Vampire | Modified BSD 3-Clause / Vampire BSD 3-Clause license | <https://github.com/vprover/vampire> |
| Optional Python benchmark dependency | huggingface_hub | Apache | <https://github.com/huggingface/huggingface_hub> |
| Optional Python symbolic backend | SymPy | BSD | <https://github.com/sympy/sympy> |
| Optional Python numerical backend | NumPy | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | <https://numpy.org> |
| Optional paper/PDF extraction backend | Docling | MIT | <https://github.com/docling-project/docling> |

## Python Transitive Dependencies

Source: `docs/operations/PYTHON_DEPENDENCY_LICENSES.md`, generated from the local Python environment metadata.

| Framework | Dependency | License | URL |
| --- | --- | --- | --- |
| Python package | accelerate 1.13.0 | Apache | <https://github.com/huggingface/accelerate> |
| Python package | alabaster 1.0.0 | BSD License | <https://alabaster.readthedocs.io/> |
| Python package | annotated-doc 0.0.4 | MIT | <https://github.com/fastapi/annotated-doc> |
| Python package | annotated-types 0.7.0 | MIT License | <https://github.com/annotated-types/annotated-types> |
| Python package | antlr4-python3-runtime 4.9.3 | BSD | <http://www.antlr.org> |
| Python package | anyio 4.13.0 | MIT | <https://github.com/agronholm/anyio> |
| Python package | attrs 26.1.0 | MIT | <https://www.attrs.org/> |
| Python package | babel 2.18.0 | BSD-3-Clause | <https://github.com/python-babel/babel> |
| Python package | beautifulsoup4 4.14.3 | MIT License | <https://www.crummy.com/software/BeautifulSoup/bs4/> |
| Python package | certifi 2026.5.20 | MPL-2.0 | <https://github.com/certifi/python-certifi> |
| Python package | charset-normalizer 3.4.7 | MIT | <https://github.com/jawah/charset_normalizer> |
| Python package | click 8.4.1 | BSD-3-Clause | <https://github.com/pallets/click/> |
| Python package | colorlog 6.10.1 | MIT License | <https://github.com/borntyping/python-colorlog> |
| Python package | contourpy 1.3.3 | BSD License | <https://github.com/contourpy/contourpy> |
| Python package | cycler 0.12.1 | BSD License | <https://matplotlib.org/cycler/> |
| Python package | defusedxml 0.7.1 | PSFL | <https://github.com/tiran/defusedxml> |
| Python package | dill 0.4.1 | BSD-3-Clause | <https://github.com/uqfoundation/dill> |
| Python package | docling 2.97.0 | MIT | <https://github.com/docling-project/docling> |
| Python package | docling-core 2.79.0 | MIT | <https://github.com/docling-project> |
| Python package | docling-ibm-models 3.13.3 | MIT | <https://github.com/docling-project/docling-ibm-models> |
| Python package | docling-parse 6.2.0 | MIT | <https://github.com/docling-project/docling-parse> |
| Python package | docling-slim 2.97.0 | MIT | <https://github.com/docling-project/docling> |
| Python package | docutils 0.22.4 | Public Domain, BSD License, GNU General Public License (GPL) | <https://docutils.sourceforge.io> |
| Python package | et_xmlfile 2.0.0 | MIT | <https://foss.heptapod.net/openpyxl/et_xmlfile> |
| Python package | Faker 40.21.0 | MIT License | <https://github.com/joke2k/faker> |
| Python package | filelock 3.29.1 | MIT | <https://github.com/tox-dev/py-filelock> |
| Python package | filetype 1.2.0 | MIT | <https://github.com/h2non/filetype.py> |
| Python package | flexcache 0.3 | BSD | <https://github.com/hgrecco/flexcache> |
| Python package | flexparser 0.4 | BSD-3-Clause | <https://github.com/hgrecco/flexparser> |
| Python package | fonttools 4.63.0 | MIT | <http://github.com/fonttools/fonttools> |
| Python package | fsspec 2026.4.0 | BSD-3-Clause | <https://github.com/fsspec/filesystem_spec> |
| Python package | h11 0.16.0 | MIT | <https://github.com/python-hyper/h11> |
| Python package | hf-xet 1.5.0 | Apache-2.0 | <https://github.com/huggingface/xet-core> |
| Python package | httpcore 1.0.9 | BSD-3-Clause | <https://www.encode.io/httpcore/> |
| Python package | httpx 0.28.1 | BSD-3-Clause | <https://github.com/encode/httpx> |
| Python package | huggingface_hub 0.36.2 | Apache | <https://github.com/huggingface/huggingface_hub> |
| Python package | hypothesis 6.155.2 | MPL-2.0 | <https://hypothesis.works> |
| Python package | idna 3.18 | BSD-3-Clause | <https://github.com/kjd/idna> |
| Python package | imagesize 2.0.0 | MIT | <https://github.com/shibukawa/imagesize_py> |
| Python package | iniconfig 2.3.0 | MIT | <https://github.com/pytest-dev/iniconfig> |
| Python package | Jinja2 3.1.6 | BSD License | <https://github.com/pallets/jinja/> |
| Python package | jsonlines 4.0.0 | BSD | <https://github.com/wbolster/jsonlines> |
| Python package | jsonref 1.1.0 | MIT | <https://github.com/gazpachoking/jsonref> |
| Python package | jsonschema 4.26.0 | MIT | <https://github.com/python-jsonschema/jsonschema> |
| Python package | jsonschema-specifications 2025.9.1 | MIT | <https://github.com/python-jsonschema/jsonschema-specifications> |
| Python package | kiwisolver 1.5.0 | BSD License | <https://github.com/nucleic/kiwi> |
| Python package | lark 1.3.1 | MIT | <https://github.com/lark-parser/lark> |
| Python package | latex2mathml 3.81.0 | MIT | <https://github.com/roniemartinez/latex2mathml> |
| Python package | latex2sympy2_extended 1.11.0 | MIT | <https://github.com/OrangeX4/latex2sympy2> |
| Python package | lxml 6.1.1 | BSD-3-Clause | <https://github.com/lxml/lxml> |
| Python package | mail-parser 4.3.0 | Apache-2.0 | <https://pypi.org/project/mail-parser/> |
| Python package | markdown-it-py 4.2.0 | MIT License | <https://github.com/executablebooks/markdown-it-py> |
| Python package | marko 2.2.3 | MIT | <https://github.com/frostming/marko> |
| Python package | MarkupSafe 3.0.3 | BSD-3-Clause | <https://github.com/pallets/markupsafe/> |
| Python package | matplotlib 3.10.9 | Python Software Foundation License | <https://matplotlib.org> |
| Python package | mdurl 0.1.2 | MIT License | <https://github.com/executablebooks/mdurl> |
| Python package | mpire 2.10.2 | MIT | <https://github.com/sybrenjansen/mpire> |
| Python package | mpmath 1.3.0 | BSD | <https://github.com/fredrik-johansson/mpmath> |
| Python package | multiprocess 0.70.19 | BSD-3-Clause | <https://github.com/uqfoundation/multiprocess> |
| Python package | narwhals 2.22.1 | MIT | <https://github.com/narwhals-dev/narwhals> |
| Python package | networkx 3.6.1 | BSD-3-Clause | <https://networkx.org/> |
| Python package | numpy 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | <https://numpy.org> |
| Python package | omegaconf 2.3.0 | BSD License | <https://github.com/omry/omegaconf> |
| Python package | opencv-python 4.13.0.92 | Apache 2.0 | <https://github.com/opencv/opencv-python> |
| Python package | openpyxl 3.1.5 | MIT | <https://foss.heptapod.net/openpyxl/openpyxl> |
| Python package | packaging 26.2 | Apache-2.0 OR BSD-2-Clause | <https://github.com/pypa/packaging> |
| Python package | pandas 3.0.3 | BSD License | <https://pandas.pydata.org> |
| Python package | pillow 12.2.0 | MIT-CMU | <https://python-pillow.github.io> |
| Python package | Pint 0.25.3 | BSD | <https://github.com/hgrecco/pint> |
| Python package | platformdirs 4.10.0 | MIT | <https://github.com/tox-dev/platformdirs> |
| Python package | plotly 6.8.0 | MIT | <https://plotly.com/python/> |
| Python package | pluggy 1.6.0 | MIT | <https://pypi.org/project/pluggy/> |
| Python package | polyfactory 3.3.0 | MIT | <https://github.com/litestar-org/polyfactory> |
| Python package | psutil 7.2.2 | BSD-3-Clause | <https://github.com/giampaolo/psutil> |
| Python package | pyclipper 1.4.0 | MIT | <https://github.com/fonttools/pyclipper> |
| Python package | pydantic 2.13.4 | MIT | <https://github.com/pydantic/pydantic> |
| Python package | pydantic-settings 2.14.1 | MIT | <https://github.com/pydantic/pydantic-settings> |
| Python package | pydantic_core 2.46.4 | MIT | <https://github.com/pydantic> |
| Python package | Pygments 2.20.0 | BSD-2-Clause | <https://pygments.org> |
| Python package | pylatexenc 2.10 | MIT | <https://github.com/phfaist/pylatexenc> |
| Python package | pyparsing 3.3.2 | MIT | <https://github.com/pyparsing/pyparsing/> |
| Python package | pypdfium2 5.9.0 | BSD-3-Clause, Apache-2.0, dependency licenses | <https://github.com/pypdfium2-team/pypdfium2> |
| Python package | pytest 9.0.3 | MIT | <https://docs.pytest.org/en/latest/> |
| Python package | python-dateutil 2.9.0.post0 | Dual License | <https://github.com/dateutil/dateutil> |
| Python package | python-docx 1.2.0 | MIT | <https://github.com/python-openxml/python-docx> |
| Python package | python-dotenv 1.2.2 | BSD-3-Clause | <https://github.com/theskumar/python-dotenv> |
| Python package | python-pptx 1.0.2 | MIT | <https://github.com/scanny/python-pptx> |
| Python package | PyYAML 6.0.3 | MIT | <https://github.com/yaml/pyyaml> |
| Python package | rapidocr 3.8.1 | Apache-2.0 | <https://rapidai.github.io/RapidOCRDocs> |
| Python package | referencing 0.37.0 | MIT | <https://github.com/python-jsonschema/referencing> |
| Python package | regex 2026.5.9 | Apache-2.0 AND CNRI-Python | <https://github.com/mrabarnett/mrab-regex> |
| Python package | requests 2.34.2 | Apache-2.0 | <https://github.com/psf/requests> |
| Python package | rich 15.0.0 | MIT | <https://github.com/Textualize/rich> |
| Python package | roman-numerals 4.1.0 | 0BSD OR CC0-1.0 | <https://github.com/AA-Turner/roman-numerals/> |
| Python package | rpds-py 2026.5.1 | MIT | <https://github.com/crate-py/rpds> |
| Python package | rtree 1.4.1 | MIT | <https://github.com/Toblerity/rtree> |
| Python package | safetensors 0.7.0 | Apache Software License | <https://github.com/huggingface/safetensors> |
| Python package | scipy 1.17.1 | BSD License | <https://scipy.org/> |
| Python package | semchunk 3.2.5 | MIT | <https://github.com/isaacus-dev/semchunk> |
| Python package | setuptools 81.0.0 | MIT | <https://github.com/pypa/setuptools> |
| Python package | shapely 2.1.2 | BSD 3-Clause | <https://github.com/shapely/shapely> |
| Python package | shellingham 1.5.4 | ISC License | <https://github.com/sarugaku/shellingham> |
| Python package | six 1.17.0 | MIT | <https://github.com/benjaminp/six> |
| Python package | snowballstemmer 3.1.1 | BSD-3-Clause | <https://github.com/snowballstem/snowball> |
| Python package | sortedcontainers 2.4.0 | Apache 2.0 | <http://www.grantjenks.com/docs/sortedcontainers/> |
| Python package | soupsieve 2.8.4 | MIT | <https://github.com/facelessuser/soupsieve> |
| Python package | Sphinx 9.1.0 | BSD-2-Clause | <https://www.sphinx-doc.org/> |
| Python package | sphinx-autodoc-typehints 3.10.5 | MIT | <https://github.com/tox-dev/sphinx-autodoc-typehints> |
| Python package | sphinxcontrib-applehelp 2.0.0 | BSD License | <https://www.sphinx-doc.org/> |
| Python package | sphinxcontrib-devhelp 2.0.0 | BSD License | <https://www.sphinx-doc.org/> |
| Python package | sphinxcontrib-htmlhelp 2.1.0 | BSD License | <https://www.sphinx-doc.org/> |
| Python package | sphinxcontrib-jsmath 1.0.1 | BSD | <http://sphinx-doc.org/> |
| Python package | sphinxcontrib-qthelp 2.0.0 | BSD License | <https://www.sphinx-doc.org/> |
| Python package | sphinxcontrib-serializinghtml 2.0.0 | BSD License | <https://www.sphinx-doc.org/> |
| Python package | sympy 1.14.0 | BSD | <https://github.com/sympy/sympy> |
| Python package | tabulate 0.10.0 | MIT | <https://github.com/astanin/python-tabulate> |
| Python package | tokenizers 0.22.2 | Apache Software License | <https://github.com/huggingface/tokenizers> |
| Python package | torch 2.12.0 | BSD-3-Clause | <https://pytorch.org> |
| Python package | torchvision 0.27.0 | BSD | <https://github.com/pytorch/vision> |
| Python package | tqdm 4.68.1 | MPL-2.0 AND MIT | <https://tqdm.github.io> |
| Python package | transformers 4.57.6 | Apache 2.0 License | <https://github.com/huggingface/transformers> |
| Python package | tree-sitter 0.25.2 | MIT License | <https://tree-sitter.github.io/tree-sitter/> |
| Python package | tree-sitter-c 0.24.2 | MIT | <https://github.com/tree-sitter/tree-sitter-c> |
| Python package | tree-sitter-javascript 0.25.0 | MIT | <https://github.com/tree-sitter/tree-sitter-javascript> |
| Python package | tree-sitter-python 0.25.0 | MIT | <https://github.com/tree-sitter/tree-sitter-python> |
| Python package | tree-sitter-typescript 0.23.2 | MIT | <https://github.com/tree-sitter/tree-sitter-typescript> |
| Python package | typer 0.21.2 | MIT | <https://github.com/fastapi/typer> |
| Python package | typing-inspection 0.4.2 | MIT | <https://github.com/pydantic/typing-inspection> |
| Python package | typing_extensions 4.15.0 | PSF-2.0 | <https://github.com/python/typing_extensions> |
| Python package | urllib3 2.7.0 | MIT | <https://github.com/urllib3/urllib3> |
| Python package | websockets 16.0 | BSD-3-Clause | <https://github.com/python-websockets/websockets> |
| Python package | xlsxwriter 3.2.9 | BSD-2-Clause | <https://github.com/jmcnamara/XlsxWriter> |
| Python package | z3-solver 4.16.0.0 | MIT License | <https://github.com/Z3Prover/z3> |
