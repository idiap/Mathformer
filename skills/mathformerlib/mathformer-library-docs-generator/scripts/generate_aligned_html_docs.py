#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Generate aligned HTML documentation for Mathformer Lean modules."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_mathformer_library_docs import (  # noqa: E402
    REPO_ROOT,
    DocComment,
    ModuleDoc,
    anchor,
    iter_lean_files,
    latex_candidates,
    load_registry_statuses,
    prose,
    rel,
    relative_link,
    scan_module,
    split_tagged_comment,
)
from generate_mathformer_library_docs import append_reasoning_log_entry  # noqa: E402

SKILL_NAME = "mathformer-library-docs-generator"
HOOK_ID = "library.aligned_html_documentation"


def page_name(module: str) -> str:
    """Document the responsibility of ``page_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``page_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"{module.replace('.', '/')}.html"


def esc(value: object) -> str:
    """Document the responsibility of ``esc``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``esc`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return html.escape(str(value), quote=True)


def render_paragraphs(lines: Sequence[str]) -> str:
    """Document the responsibility of ``render_paragraphs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = prose(lines).strip()
    if not text:
        return ""
    return "\n".join(f"<p>{esc(paragraph)}</p>" for paragraph in text.split("\n\n"))


def render_latex_block(lines: Sequence[str], label: str) -> str:
    """Document the responsibility of ``render_latex_block``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not lines:
        return ""
    raw = "\n".join(lines).strip()
    candidates = latex_candidates(lines)[:4]
    rendered = [
        '<div class="source-subsection">',
        f"<h4>{esc(label)}</h4>",
        '<pre class="latex-source"><code class="language-latex">',
        esc(raw),
        "</code></pre>",
    ]
    if candidates:
        rendered.append('<div class="math-preview" aria-label="Rendered LaTeX">')
        for candidate in candidates:
            rendered.append(f'<div class="math-display">\\[{esc(candidate)}\\]</div>')
        rendered.append("</div>")
    rendered.append("</div>")
    return "\n".join(rendered)


def render_source_comment(comment: Optional[DocComment]) -> str:
    """Document the responsibility of ``render_source_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if comment is None or not comment.body.strip():
        return (
            '<p class="empty-note">No source annotation is attached to this '
            "formal object.</p>"
        )
    sections = split_tagged_comment(comment.body)
    parts: List[str] = []
    if "original_nl" in sections:
        parts.append('<div class="source-subsection original-text">')
        parts.append("<h4>Original Text</h4>")
        parts.append(render_paragraphs(sections["original_nl"]))
        parts.append("</div>")
    if "original_latex" in sections:
        parts.append(render_latex_block(sections["original_latex"], "Original LaTeX"))
    if "generated_nl" in sections:
        parts.append('<div class="source-subsection generated-text">')
        parts.append("<h4>Generated Commentary</h4>")
        parts.append(render_paragraphs(sections["generated_nl"]))
        parts.append("</div>")
    if "generated_latex" in sections:
        parts.append(render_latex_block(sections["generated_latex"], "Generated LaTeX"))
    if "other" in sections:
        parts.append('<div class="source-subsection generated-text">')
        parts.append("<h4>Additional Comment</h4>")
        parts.append(render_paragraphs(sections["other"]))
        parts.append("</div>")
    if not parts:
        return '<p class="empty-note">The attached comment has no recognized source sections.</p>'
    return "\n".join(parts)


def declaration_title(decl_comment: Optional[DocComment], fallback: str) -> str:
    """Document the responsibility of ``declaration_title``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``declaration_title`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if decl_comment is None:
        return fallback
    sections = split_tagged_comment(decl_comment.body)
    source = prose(sections.get("original_nl", []) or sections.get("generated_nl", []))
    if not source:
        return fallback
    sentence = re.split(r"(?<=[.!?])\s+", source.strip(), maxsplit=1)[0]
    return sentence[:160] + ("..." if len(sentence) > 160 else "")


def render_imports(module: ModuleDoc) -> str:
    """Document the responsibility of ``render_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not module.imports:
        return ""
    imports = "\n".join(f"import {item}" for item in module.imports)
    return (
        '<section class="imports" aria-labelledby="imports-title">'
        '<h2 id="imports-title">Imports</h2>'
        '<pre><code class="language-lean">'
        f"{esc(imports)}"
        "</code></pre>"
        "</section>"
    )


def render_toc(module: ModuleDoc, page_file: Path) -> str:
    """Document the responsibility of ``render_toc``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_link = relative_link(page_file, REPO_ROOT / module.rel_path)
    items = []
    for decl in module.declarations:
        items.append(
            "<li>"
            f'<a href="#{anchor(decl.qualified_name)}">{esc(decl.qualified_name)}</a>'
            f"<span>{esc(decl.kind)} at "
            f'<a href="{esc(source_link)}#L{decl.line}">line {decl.line}</a></span>'
            "</li>"
        )
    if not items:
        items.append("<li><span>No declarations parsed.</span></li>")
    return (
        '<nav class="toc" aria-labelledby="toc-title">'
        '<h2 id="toc-title">Formal Objects</h2>'
        "<ol>" + "\n".join(items) + "</ol></nav>"
    )


def render_declaration(module: ModuleDoc, decl: Any, page_file: Path) -> str:
    """Document the responsibility of ``render_declaration``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_link = relative_link(page_file, REPO_ROOT / module.rel_path)
    title = declaration_title(decl.comment, decl.qualified_name)
    has_original = False
    if decl.comment is not None:
        sections = split_tagged_comment(decl.comment.body)
        has_original = bool(
            sections.get("original_nl") or sections.get("original_latex")
        )
    source_badge = "Original source" if has_original else "Generated bridge"
    return f"""
<article class="alignment-block" id="{anchor(decl.qualified_name)}" data-kind="{esc(decl.kind)}">
  <header class="alignment-heading">
    <div>
      <p class="eyebrow">{esc(source_badge)} to Lean alignment</p>
      <h2>{esc(title)}</h2>
    </div>
    <a class="line-link" href="{esc(source_link)}#L{decl.line}">{esc(module.rel_path)}:{decl.line}</a>
  </header>
  <div class="alignment-grid">
    <section class="source-panel" aria-label="Textual mention">
      <h3>Textual Mention</h3>
      {render_source_comment(decl.comment)}
    </section>
    <section class="formal-panel" aria-label="Formalized version">
      <h3>Formalized Version</h3>
      <div class="formal-meta">
        <span>{esc(decl.kind)}</span>
        <strong>{esc(decl.qualified_name)}</strong>
      </div>
      <pre><code class="language-lean">{esc(decl.code)}</code></pre>
    </section>
  </div>
</article>
""".strip()


def render_styles() -> str:
    """Document the responsibility of ``render_styles``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return """
:root {
  color-scheme: light;
  --bg: #f6f7f2;
  --ink: #1f2524;
  --muted: #66736f;
  --panel: #ffffff;
  --line: #d9ded7;
  --source: #5f6f00;
  --formal: #0f6f6a;
  --code-bg: #0f1615;
  --code-ink: #edf7f3;
  --soft-source: #fbfaea;
  --soft-formal: #eef8f6;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
}

a {
  color: #086c67;
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.18em;
}

.page-header {
  border-bottom: 1px solid var(--line);
  background: #ffffff;
}

.page-header-inner,
main {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
}

.page-header-inner {
  padding: 28px 0 22px;
}

.crumb {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 0.9rem;
}

h1 {
  margin: 0;
  font-size: clamp(1.7rem, 3vw, 2.6rem);
  line-height: 1.08;
  letter-spacing: 0;
}

.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.summary span,
.formal-meta span,
.line-link {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #f8faf6;
  color: var(--muted);
  font-size: 0.82rem;
  padding: 4px 10px;
}

main {
  padding: 24px 0 54px;
}

.module-notes,
.imports,
.toc,
.source-panel,
.formal-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.module-notes,
.imports,
.toc {
  padding: 18px;
  margin-bottom: 18px;
}

h2,
h3,
h4 {
  letter-spacing: 0;
}

h2 {
  margin: 0 0 12px;
  font-size: 1.15rem;
}

h3 {
  margin: 0 0 14px;
  font-size: 0.98rem;
}

h4 {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 0.8rem;
  text-transform: uppercase;
}

.toc ol {
  margin: 0;
  padding-left: 22px;
}

.toc li {
  margin: 7px 0;
}

.toc li span {
  color: var(--muted);
  display: inline-block;
  margin-left: 8px;
  font-size: 0.88rem;
}

.alignment-block {
  padding: 28px 0;
  border-top: 1px solid var(--line);
}

.alignment-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 14px;
}

.alignment-heading h2 {
  margin: 0;
  max-width: 820px;
  font-size: 1.18rem;
  line-height: 1.35;
}

.eyebrow {
  margin: 0 0 5px;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

.line-link {
  flex: 0 0 auto;
  text-decoration: none;
}

.alignment-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: 14px;
  align-items: start;
}

.source-panel,
.formal-panel {
  min-width: 0;
  padding: 16px;
}

.source-panel {
  background: var(--soft-source);
}

.formal-panel {
  background: var(--soft-formal);
}

.source-subsection + .source-subsection {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(95, 111, 0, 0.18);
}

.source-subsection p,
.module-notes p {
  margin: 0 0 10px;
}

.empty-note {
  color: var(--muted);
  font-style: italic;
}

.formal-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  min-width: 0;
}

.formal-meta strong {
  min-width: 0;
  overflow-wrap: anywhere;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  font-size: 0.9rem;
}

pre {
  max-width: 100%;
  overflow-x: auto;
  margin: 0;
  border-radius: 8px;
  background: var(--code-bg);
  color: var(--code-ink);
  padding: 14px;
  font-size: 0.86rem;
  line-height: 1.48;
}

.latex-source {
  background: #292915;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}

.math-preview {
  margin-top: 10px;
  padding: 10px;
  overflow-x: auto;
  border: 1px solid rgba(95, 111, 0, 0.22);
  border-radius: 8px;
  background: #ffffff;
}

.math-display {
  min-width: 0;
}

footer {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 22px 0 36px;
  color: var(--muted);
  border-top: 1px solid var(--line);
  font-size: 0.9rem;
}

@media (max-width: 860px) {
  .alignment-heading,
  .alignment-grid {
    display: block;
  }

  .line-link {
    display: inline-block;
    margin-top: 12px;
  }

  .formal-panel {
    margin-top: 12px;
  }

  .page-header-inner,
  main,
  footer {
    width: min(100vw - 22px, 1180px);
  }
}
""".strip()


def render_module_page(module: ModuleDoc, output_dir: Path) -> str:
    """Document the responsibility of ``render_module_page``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    page_file = output_dir / page_name(module.module)
    index_link = relative_link(page_file, output_dir / "INDEX.html")
    source_link = relative_link(page_file, REPO_ROOT / module.rel_path)
    generated_at = datetime.now(timezone.utc).isoformat()
    module_notes = ""
    if module.module_comment is not None:
        module_notes = (
            '<section class="module-notes" aria-labelledby="module-notes-title">'
            '<h2 id="module-notes-title">Chapter Source Flow</h2>'
            f"{render_source_comment(module.module_comment)}"
            "</section>"
        )
    declarations = "\n".join(
        render_declaration(module, decl, page_file) for decl in module.declarations
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(module.module)} aligned formalization</title>
  <style>{render_styles()}</style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github-dark.min.css">
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
      }},
      svg: {{ fontCache: 'global' }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/common.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/lean.min.js"></script>
  <script defer>window.addEventListener('DOMContentLoaded', function () {{ if (window.hljs) {{ window.hljs.highlightAll(); }} }});</script>
</head>
<body>
  <header class="page-header">
    <div class="page-header-inner">
      <p class="crumb"><a href="{esc(index_link)}">Aligned Mathformer Library</a> / <a href="{esc(source_link)}">{esc(module.rel_path)}</a></p>
      <h1>{esc(module.module)}</h1>
      <div class="summary" aria-label="Module summary">
        <span>Status: {esc(module.status)}</span>
        <span>Declarations: {len(module.declarations)}</span>
        <span>Generated: {esc(generated_at)}</span>
        <span>SHA-256: {esc(module.sha256[:12])}</span>
      </div>
    </div>
  </header>
  <main>
    {module_notes}
    {render_imports(module)}
    {render_toc(module, page_file)}
    {declarations}
  </main>
  <footer>
    Generated by {esc(SKILL_NAME)} using hook {esc(HOOK_ID)}. Textual mentions are aligned with the Lean declarations in source order.
  </footer>
</body>
</html>
"""


def render_index(modules: Sequence[ModuleDoc], output_dir: Path) -> str:
    """Document the responsibility of ``render_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    items = []
    for module in sorted(modules, key=lambda item: item.module):
        page = output_dir / page_name(module.module)
        source = REPO_ROOT / module.rel_path
        items.append(
            "<tr>"
            f'<td><a href="{esc(relative_link(output_dir / "INDEX.html", page))}">{esc(module.module)}</a></td>'
            f"<td>{esc(module.status)}</td>"
            f"<td>{len(module.declarations)}</td>"
            f'<td><a href="{esc(relative_link(output_dir / "INDEX.html", source))}">{esc(module.rel_path)}</a></td>'
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aligned Mathformer Library</title>
  <style>
    body {{ margin: 0; background: #f6f7f2; color: #1f2524; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.55; }}
    main {{ width: min(980px, calc(100vw - 32px)); margin: 0 auto; padding: 32px 0 56px; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(1.8rem, 3vw, 2.5rem); letter-spacing: 0; }}
    p {{ color: #66736f; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9ded7; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 11px 12px; border-bottom: 1px solid #d9ded7; text-align: left; vertical-align: top; }}
    th {{ background: #eef8f6; }}
    a {{ color: #086c67; }}
  </style>
</head>
<body>
  <main>
    <h1>Aligned Mathformer Library</h1>
    <p>Generated at {esc(generated_at)}. Each page follows the Lean source order and aligns textual or LaTeX mentions with the formalized declarations.</p>
    <table>
      <thead><tr><th>Module</th><th>Status</th><th>Declarations</th><th>Lean Source</th></tr></thead>
      <tbody>{''.join(items)}</tbody>
    </table>
  </main>
</body>
</html>
"""


def build_docs(
    roots: Sequence[Path],
    output_dir: Path,
    registry_file: Optional[Path],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_docs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    registry_statuses = load_registry_statuses(registry_file)
    modules = [scan_module(path, registry_statuses) for path in iter_lean_files(roots)]
    output_dir = (REPO_ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    written_pages: List[str] = []
    for module in modules:
        page = output_dir / page_name(module.module)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(render_module_page(module, output_dir), encoding="utf-8")
        written_pages.append(rel(page))

    index_file = output_dir / "INDEX.html"
    index_file.write_text(render_index(modules, output_dir), encoding="utf-8")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": bool(modules),
        "roots": [str(root) for root in roots],
        "output_dir": rel(output_dir),
        "index_file": rel(index_file),
        "summary": {
            "module_count": len(modules),
            "declaration_count": sum(len(module.declarations) for module in modules),
            "module_page_count": len(written_pages),
            "aligned_block_count": sum(len(module.declarations) for module in modules),
        },
        "modules": [
            {
                "module": module.module,
                "path": module.rel_path,
                "status": module.status,
                "page": written_pages[index],
                "declaration_count": len(module.declarations),
            }
            for index, module in enumerate(modules)
        ],
    }
    manifest_file = output_dir / "manifest.json"
    manifest_file.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["manifest_file"] = rel(manifest_file)
    return manifest


def append_event(
    reasoning_log: Optional[Path], step: str, payload: Dict[str, Any]
) -> None:
    """Document the responsibility of ``append_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if reasoning_log is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def render_text(manifest: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summary = manifest["summary"]
    lines = [
        f"ok: {manifest['ok']}",
        f"index: {manifest['index_file']}",
        f"modules: {summary['module_count']}",
        f"declarations: {summary['declaration_count']}",
        f"aligned_blocks: {summary['aligned_block_count']}",
    ]
    for module in manifest["modules"]:
        lines.append(
            f"- {module['status']} {module['module']} "
            f"decls={module['declaration_count']} page={module['page']}"
        )
    return "\n".join(lines)


def run_self_test() -> Dict[str, Any]:
    """Document the responsibility of ``run_self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fixture_dir = REPO_ROOT / "artifacts" / "aligned_html_docs_self_test"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    fixture = fixture_dir / "Fixture.lean"
    fixture.write_text(
        """
import Mathlib

/-!
Original source (NL): A tiny chapter states that zero equals zero.
Original source (LaTeX): `0=0`.
Generated note (NL): This checks module-level alignment.
-/

namespace Fixture

/--
Original source (NL): Zero is equal to itself.
Original source (LaTeX): `0=0`.
Generated note (NL): The formal proof is reflexivity.
-/
theorem zero_eq_zero : (0 : Nat) = 0 := by
  rfl

/--
Generated note (NL): A generated bridge object should still be aligned.
Generated equivalent (LaTeX): `1=1`.
-/
theorem one_eq_one : (1 : Nat) = 1 := by
  rfl

end Fixture
""".lstrip(),
        encoding="utf-8",
    )
    output_dir = Path("artifacts/aligned_html_docs_self_test/docs")
    manifest = build_docs([fixture.relative_to(REPO_ROOT)], output_dir, None)
    page = REPO_ROOT / manifest["modules"][0]["page"]
    text = page.read_text(encoding="utf-8")
    checks = {
        "has_mathjax": "tex-svg.js" in text,
        "has_highlight": "highlight.js" in text and "language-lean" in text,
        "has_alignment_blocks": text.count('class="alignment-block"') == 2,
        "has_original_text": "Zero is equal to itself" in text,
        "has_generated_bridge": "Generated bridge" in text,
        "has_latex_preview": "\\[0=0\\]" in text,
    }
    return {
        "ok": all(checks.values()) and manifest["summary"]["module_page_count"] == 1,
        "checks": checks,
        "manifest": manifest,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lean-file",
        action="append",
        type=Path,
        default=[],
        help="Lean file to render. May be passed multiple times.",
    )
    parser.add_argument(
        "--include-root",
        action="append",
        type=Path,
        default=[],
        help="Lean file or directory to include when --lean-file is not used.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/libraries/mathformerlib/aligned")
    )
    parser.add_argument("--registry-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--expect-docs", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 3

    roots = (
        args.lean_file
        or args.include_root
        or [Path("MathformerLib"), Path("Mathformer")]
    )
    append_event(
        args.reasoning_log_file,
        "mathformer_aligned_html_docs_start",
        {
            "roots": [str(root) for root in roots],
            "output_dir": str(args.output_dir),
            "registry_file": str(args.registry_file) if args.registry_file else None,
        },
    )
    manifest = build_docs(roots, args.output_dir, args.registry_file)
    append_event(
        args.reasoning_log_file,
        "mathformer_aligned_html_docs_complete",
        {
            "ok": manifest["ok"],
            **manifest["summary"],
            "index_file": manifest["index_file"],
        },
    )
    if args.expect_docs and not manifest["ok"]:
        append_event(
            args.reasoning_log_file,
            "mathformer_aligned_html_docs_error",
            {"reason": "no aligned HTML docs generated"},
        )
        if args.json:
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            print(render_text(manifest))
        return 3
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_text(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
