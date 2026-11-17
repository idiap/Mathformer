#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Automate repository maintenance tasks that would be error-prone if performed by hand.
#
# Intent:
#   Expose command-line entry points for setup, generation, indexing, auditing, and proof execution.
#
# Function:
#   Implements operational glue used by tests, skills, docs, and developer workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Generate a Markdown license inventory from installed Python metadata."""

from __future__ import annotations

import argparse
import re
import sys
from importlib import metadata
from pathlib import Path

PREFERRED_URL_LABELS = (
    "homepage",
    "home-page",
    "repository",
    "source",
    "source code",
    "code",
    "documentation",
)


def clean(value: str | None, *, max_len: int = 140) -> str:
    """Document the responsibility of ``clean``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``clean`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not value:
        return ""
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3].rstrip() + "..."


def escape_table(value: str) -> str:
    """Document the responsibility of ``escape_table``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``escape_table`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return value.replace("|", r"\|").replace("\n", " ")


def license_summary(meta: metadata.PackageMetadata) -> str:
    """Document the responsibility of ``license_summary``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``license_summary`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    expression = clean(
        (meta["License-Expression"] if "License-Expression" in meta else None)
    )
    if expression:
        return expression

    classifiers = [
        c.split(" :: ")[-1]
        for c in (meta.get_all("Classifier") or [])
        if c.startswith("License ::")
    ]
    license_field = clean((meta["License"] if "License" in meta else None))
    if license_field and len(license_field) <= 80:
        return license_field
    if classifiers:
        return ", ".join(dict.fromkeys(classifiers))
    return license_field or "UNKNOWN"


def project_url(meta: metadata.PackageMetadata) -> str:
    """Document the responsibility of ``project_url``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``project_url`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    home_page = clean((meta["Home-page"] if "Home-page" in meta else None), max_len=220)
    project_urls = meta.get_all("Project-URL") or []
    parsed: list[tuple[str, str]] = []
    for raw in project_urls:
        if "," not in raw:
            continue
        label, url = raw.split(",", 1)
        parsed.append((label.strip().lower(), url.strip()))

    for preferred in PREFERRED_URL_LABELS:
        for label, url in parsed:
            if label == preferred:
                return url
    if parsed:
        return parsed[0][1]
    return home_page


def package_rows() -> list[tuple[str, str, str, str]]:
    """Document the responsibility of ``package_rows``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Provide the local operation named ``package_rows`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows: list[tuple[str, str, str, str]] = []
    for dist in metadata.distributions():
        meta = dist.metadata
        name = clean(
            (meta["Name"] if "Name" in meta else None) or getattr(dist, "name", ""),
            max_len=80,
        )
        version = clean((meta["Version"] if "Version" in meta else None), max_len=60)
        rows.append((name, version, license_summary(meta), project_url(meta)))
    return sorted(rows, key=lambda row: row[0].lower())


def render(rows: list[tuple[str, str, str, str]]) -> str:
    """Document the responsibility of ``render``.

    Motivation:
        Automate repository maintenance tasks that would be error-prone if performed by hand.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        "<!--",
        "# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>",
        "#",
        "# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>",
        "# Neuro-symbolic AI Group",
        "#",
        # REUSE-IgnoreStart
        "# SPDX-License-Identifier: MIT",
        # REUSE-IgnoreEnd
        "-->",
        "",
        "# Python Dependency License Inventory",
        "",
        "This report is generated from the installed Python environment metadata.",
        "It is an inventory aid, not legal advice. Wheel metadata can omit bundled",
        "native library notices, model licenses, or dataset terms, so verify upstream",
        "license files before redistributing an environment or binary artifact.",
        "",
        f"- Python executable: `{sys.executable}`",
        f"- Python version: `{sys.version.split()[0]}`",
        f"- Installed distributions listed: `{len(rows)}`",
        "",
        "After activating the environment you want to inventory, regenerate from",
        "the repository root with:",
        "",
        "```bash",
        "python scripts/generate_python_license_inventory.py \\",
        "  --output docs/operations/PYTHON_DEPENDENCY_LICENSES.md",
        "```",
        "",
        "| Package | Version | License metadata | Project URL |",
        "| --- | --- | --- | --- |",
    ]
    for name, version, license_text, url in rows:
        url_text = f"<{url}>" if url else ""
        lines.append(
            "| "
            + " | ".join(
                escape_table(value) for value in (name, version, license_text, url_text)
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the native CLI, retaining argparse help and error exits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/operations/PYTHON_DEPENDENCY_LICENSES.md"),
        help="Markdown file to write.",
    )
    return parser.parse_args(argv)


def create_directory(output: Path) -> bool:
    """Create the destination parent after rendering succeeds."""
    output.parent.mkdir(parents=True, exist_ok=True)
    return True


def write_inventory(output: Path, content: str) -> int:
    """Overwrite the UTF-8 inventory and retain native completion printing."""
    output.write_text(content, encoding="utf-8")
    print(f"wrote {output}")
    return 0


def main() -> int:
    """Coordinate the same shared steps used by the MCP bindings."""
    args = parse_arguments()
    content = render(package_rows())
    create_directory(args.output)
    return write_inventory(args.output, content)


if __name__ == "__main__":
    raise SystemExit(main())
