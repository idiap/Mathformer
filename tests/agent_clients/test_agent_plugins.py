#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise plugin generation and checkout-independent distribution layout."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
import shutil
import tempfile
import unittest
import hashlib
import sys
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "sync_agent_plugins", ROOT / "scripts/sync_agent_plugins.py"
)
assert SPEC and SPEC.loader
plugins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plugins)
sys.path.insert(0, str(ROOT / "scripts"))
from workflow_catalog import WORKFLOWS, load_catalog, plugin_skill_name  # noqa: E402


class AgentPluginTests(unittest.TestCase):
    """Check discovery parity and changes that previously risked silent drift."""

    def fixture(self, root: Path) -> Path:
        """Create a minimal source tree, including legacy pre-frontmatter comments."""
        (root / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
        (root / "LICENSE").write_text("MIT\n")
        (root / "LICENSES").mkdir()
        (root / "LICENSES/MIT.txt").write_text("MIT\n")
        source = root / "skills/lean/demo/SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "<!-- license -->\n\n---\nname: demo\ndescription: Execute a demo.\n---\nBody\n"
        )
        return source

    def test_reuse_annotations_only_cover_comment_free_files_and_skill_markdown(self):
        """Directory globs must not silently replace native source headers."""
        for manifest in (ROOT / "REUSE.toml", ROOT / plugins.PLUGIN / "REUSE.toml"):
            metadata = tomllib.loads(manifest.read_text())
            for annotation in metadata["annotations"]:
                for name in annotation["path"]:
                    path = Path(name)
                    self.assertFalse(any(char in name for char in "*?[]"), name)
                    skill_markdown = path.suffix == ".md" and any(
                        "skill" in part for part in path.parts[:-1]
                    )
                    comment_free = path.suffix in {".json", ".jsonl", ".txt"} or (
                        path.name in {"LICENSE", "lean-toolchain"}
                    )
                    self.assertTrue(skill_markdown or comment_free, name)
                    self.assertFalse(path.name.startswith("requirements"), name)

    def test_repository_is_current(self):
        self.assertEqual(plugins.synchronize(ROOT, check=True), [])
        canonical = list((ROOT / "skills").glob("*/*/SKILL.md"))
        discovered = list((ROOT / plugins.PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertEqual(
            {p.parent.name for p in canonical}
            | {plugin_skill_name(row["id"]) for row in load_catalog()["workflows"]},
            {p.parent.name for p in discovered},
        )

    def test_drift_and_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.fixture(root)
            plugins.synchronize(root, check=False)
            self.assertEqual(plugins.synchronize(root, check=True), [])
            entry = root / plugins.PLUGIN / "skills/demo/SKILL.md"
            self.assertNotIn("SPDX-", entry.read_text())
            self.assertEqual(
                ["Andre Freitas <andre.freitas@idiap.ch>"],
                plugins.contributors_for(root, entry.relative_to(root)),
            )
            source.write_text(
                source.read_text().replace("Execute a demo.", "Execute a changed demo.")
            )
            before = entry.read_bytes()
            self.assertIn(
                str(entry.relative_to(root)), plugins.synchronize(root, check=True)
            )
            self.assertEqual(entry.read_bytes(), before)
            plugins.synchronize(root, check=False)
            renamed = source.parent.with_name("renamed")
            source.parent.rename(renamed)
            (renamed / "SKILL.md").write_text(
                (renamed / "SKILL.md")
                .read_text()
                .replace("name: demo", "name: renamed")
            )
            plugins.synchronize(root, check=False)
            self.assertFalse(entry.exists())
            self.assertTrue((entry.parent.with_name("renamed") / "SKILL.md").exists())

    def test_duplicate_names_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.fixture(root)
            duplicate = root / "skills/control/demo"
            duplicate.mkdir(parents=True)
            shutil.copy2(source, duplicate / "SKILL.md")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                plugins.expected_files(root)

    def test_cached_plugin_is_self_contained_for_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            cached = Path(directory) / "cache/mathformer"
            shutil.copytree(ROOT / plugins.PLUGIN, cached)
            for client in ("codex", "claude"):
                manifest = json.loads(
                    (cached / f".{client}-plugin/plugin.json").read_text()
                )
                self.assertEqual(manifest["name"], "mathformer")
                skill_root = cached / manifest.get("skills", "./skills/")
                self.assertEqual(
                    len(list(skill_root.glob("*/SKILL.md"))),
                    len(list((ROOT / "skills").glob("*/*/SKILL.md")))
                    + len(load_catalog()["workflows"]),
                )
            for entry in (cached / "skills").glob("*/SKILL.md"):
                self.assertFalse(entry.is_symlink())
                self.assertTrue(entry.read_text().startswith("---\n"))
                self.assertNotIn("SPDX-", entry.read_text())
                self.assertNotIn(str(ROOT), entry.read_text())
            self.assertEqual(
                (cached / "REUSE.toml").read_text(),
                plugins.expected_files(ROOT)[plugins.PLUGIN / "REUSE.toml"],
            )
            self.assertEqual(
                (cached / "LICENSES/MIT.txt").read_bytes(),
                (ROOT / "LICENSES/MIT.txt").read_bytes(),
            )
            for marketplace in (
                ".agents/plugins/marketplace.json",
                ".claude-plugin/marketplace.json",
            ):
                entry = json.loads((ROOT / marketplace).read_text())["plugins"][0]
                source = entry["source"]
                path = source["path"] if isinstance(source, dict) else source
                self.assertEqual(
                    (ROOT / path).resolve(), (ROOT / plugins.PLUGIN).resolve()
                )

    def test_every_workflow_has_a_cached_contract_in_both_clients(self):
        catalog = load_catalog()
        plugin_catalog = json.loads(
            (ROOT / plugins.PLUGIN / "workflow-catalog.json").read_text()
        )
        self.assertEqual(
            {row["id"] for row in plugin_catalog["workflows"]},
            {row["id"] for row in catalog["workflows"]},
        )
        self.assertEqual(plugin_catalog["counts"], catalog["counts"])
        for row in plugin_catalog["workflows"]:
            path = ROOT / plugins.PLUGIN / row["path"]
            content = path.read_bytes()
            self.assertEqual(
                row["descriptor_digest"],
                "sha256:" + hashlib.sha256(content).hexdigest(),
            )
            original = (
                ROOT
                / WORKFLOWS
                / next(
                    item["path"]
                    for item in catalog["workflows"]
                    if item["id"] == row["id"]
                )
            ).read_text()
            self.assertTrue(content.decode().endswith(original))
            self.assertLessEqual(len(row["plugin_skill"]), 64)
            for client in ("codex", "claude"):
                manifest = json.loads(
                    (
                        ROOT / plugins.PLUGIN / f".{client}-plugin/plugin.json"
                    ).read_text()
                )
                entry = (
                    ROOT
                    / plugins.PLUGIN
                    / manifest.get("skills", "./skills/")
                    / row["plugin_skill"]
                    / "SKILL.md"
                )
                self.assertTrue(entry.is_file())
                self.assertIn(row["id"], entry.read_text())

    def test_plugin_retains_canonical_contributors(self):
        self.assertLessEqual(
            set(plugins.contributors_for(ROOT, Path("LICENSE"))),
            set(plugins.contributors_for(ROOT, plugins.PLUGIN / "LICENSE")),
        )
        metadata = tomllib.loads((ROOT / plugins.PLUGIN / "REUSE.toml").read_text())
        self.assertTrue(
            all(item["precedence"] == "override" for item in metadata["annotations"])
        )
        for source in (ROOT / "skills").glob("*/*/SKILL.md"):
            entry = plugins.PLUGIN / "skills" / source.parent.name / "SKILL.md"
            self.assertLessEqual(
                set(plugins.contributors_for(ROOT, source.relative_to(ROOT))),
                set(plugins.contributors_for(ROOT, entry)),
            )

    # REUSE-IgnoreStart
    # These assertions inspect generated metadata rather than this file's license.
    def test_generated_metadata_uses_toml_without_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            expected = plugins.expected_files(root)
            self.assertFalse(any(path.suffix == ".license" for path in expected))
            plugins.synchronize(root, check=False)
            self.assertFalse(list(root.rglob("*.license")))
            metadata = tomllib.loads((root / plugins.PLUGIN / "REUSE.toml").read_text())
            for path in expected:
                if not path.is_relative_to(plugins.PLUGIN):
                    continue
                if path.suffix != ".json" and path.name != "LICENSE":
                    continue
                relative = path.relative_to(plugins.PLUGIN).as_posix()
                annotations = [
                    item for item in metadata["annotations"] if relative in item["path"]
                ]
                self.assertTrue(annotations, path)
                self.assertEqual(annotations[-1]["SPDX-License-Identifier"], "MIT")
                self.assertEqual(
                    annotations[-1]["SPDX-FileCopyrightText"],
                    "Copyright © 2026 Idiap Research Institute <contact@idiap.ch>",
                )

    # REUSE-IgnoreEnd

    def test_repository_contributor_scope(self):
        """Keep Danilo attribution scoped to PRISM and MCP server files."""
        tracked = (
            subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
            .decode()
            .split("\0")
        )
        for name in tracked:
            path = ROOT / name
            if not name or not path.is_file() or path.is_symlink():
                continue
            if name.startswith("vendor/") or "LICENSES" in path.parts:
                continue
            allowed = (
                bool(re.search(r"(^|[/_.-])(prism|mcp)([/_.-]|$)", name.lower()))
                or name == "scripts/workflow_catalog.py"
            )
            if not allowed:
                self.assertNotIn(
                    "Danilo Gusicuma <danilo.gusicuma@idiap.ch>",
                    plugins.contributors_for(ROOT, Path(name)),
                    name,
                )

    def test_cached_workflow_schemas_and_dataflow_are_self_contained(self):
        sys.path.insert(
            0, str(ROOT / "skills/control/workflow-contract-validator/scripts")
        )
        import validate_workflow as contract_validator
        from jsonschema import Draft202012Validator

        with tempfile.TemporaryDirectory() as directory:
            cached = (Path(directory) / "mathformer").resolve()
            shutil.copytree(ROOT / plugins.PLUGIN, cached)
            schema = json.loads((cached / "workflow.schema.json").read_text())
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            catalog = json.loads((cached / "workflow-catalog.json").read_text())
            for row in catalog["workflows"]:
                path = cached / row["path"]
                descriptor = contract_validator.load_yaml(path)
                validator.validate(descriptor)
                self.assertEqual(
                    contract_validator.Semantics(
                        descriptor, path.parent, cached
                    ).validate(),
                    [],
                )

    def test_workflow_alias_names_are_portable_and_unique(self):
        names = [plugin_skill_name(row["id"]) for row in load_catalog()["workflows"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(len(name) <= 64 for name in names))
        self.assertNotEqual(
            plugin_skill_name("a" * 80 + "_workflow"),
            plugin_skill_name("a" * 79 + "b_workflow"),
        )

    def test_missing_catalog_cannot_silently_remove_workflow_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            schema = root / WORKFLOWS.parent / "workflow.schema.json"
            schema.parent.mkdir(parents=True, exist_ok=True)
            schema.write_text("{}")
            with self.assertRaisesRegex(ValueError, "catalog missing"):
                plugins.expected_files(root)

    def test_removal_of_workflow_entry_preserves_unmanaged_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            stale = root / plugins.PLUGIN / "skills/obsolete"
            stale.mkdir(parents=True)
            (stale / "SKILL.md").write_text(
                "Generated by `scripts/sync_agent_plugins.py`\n"
            )
            (stale / "workflow.yaml").write_text(
                "# Generated by `scripts/sync_agent_plugins.py`; old\n"
            )
            (stale / "user-notes.md").write_text("retain")
            plugins.synchronize(root, check=False)
            self.assertFalse((stale / "SKILL.md").exists())
            self.assertFalse((stale / "workflow.yaml").exists())
            self.assertEqual((stale / "user-notes.md").read_text(), "retain")


if __name__ == "__main__":
    unittest.main()
