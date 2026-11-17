# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Portable packager behavior; no repository imports or third-party dependencies."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "build_transfer.py"
SPEC = importlib.util.spec_from_file_location("build_transfer", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildTransferTests(unittest.TestCase):
    def test_complete_archive_and_relative_guide_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "kit.zip"
            builder.build(target)
            with ZipFile(target) as archive:
                manifest = json.loads(archive.read("transfer-manifest.json"))
                self.assertEqual(manifest["artifact_type"], "agent-adoption-kit")
                self.assertEqual(manifest["kit_version"], "1.2")
                for name, checksum in manifest["files"].items():
                    self.assertFalse(Path(name).is_absolute())
                    self.assertNotIn("..", Path(name).parts)
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), checksum)
                archive.extractall(root / "extracted")
            skill = root / "extracted" / builder.PACKAGE
            self.assertTrue((skill / "../../../docs/portable-repository-adoption.md").resolve().is_file())
            builder.verify_archive(target, manifest)

    def test_existing_destination_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "kit.zip"
            target.write_bytes(b"existing content")
            with self.assertRaises(FileExistsError):
                builder.build(target)
            self.assertEqual(target.read_bytes(), b"existing content")
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_missing_source_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "kit.zip"
            with patch.object(builder, "PATHS", ["missing-adoption-fixture-source"]):
                with self.assertRaises(FileNotFoundError):
                    builder.build(target)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_write_validation_and_publication_failures_leave_no_archive(self):
        for component, method in [(builder.ZipFile, "writestr"),
                                  (builder, "verify_archive"), (builder.os, "link")]:
            with self.subTest(method=method), tempfile.TemporaryDirectory() as directory:
                with patch.object(component, method, side_effect=OSError("induced failure")):
                    with self.assertRaises(OSError):
                        builder.build(Path(directory) / "kit.zip")
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_corrupt_payload_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "kit.zip"
            manifest = {"files": {"payload": hashlib.sha256(b"original").hexdigest()}}
            with ZipFile(target, "w") as archive:
                archive.writestr("payload", b"changed")
                archive.writestr("transfer-manifest.json", json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "checksum"):
                builder.verify_archive(target, manifest)


if __name__ == "__main__":
    unittest.main()
