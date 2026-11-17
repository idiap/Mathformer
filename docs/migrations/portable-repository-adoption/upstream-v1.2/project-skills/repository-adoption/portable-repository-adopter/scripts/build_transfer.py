# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Package the explicit adoption-guide closure; no application code is executed."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


PACKAGE = "project-skills/repository-adoption/portable-repository-adopter"
PATHS = [
        "docs/portable-repository-adoption.md",
        f"{PACKAGE}/SKILL.md",
        f"{PACKAGE}/scripts/build_transfer.py",
        f"{PACKAGE}/scripts/example_runtime.py",
        f"{PACKAGE}/tests/test_example_runtime.py",
        f"{PACKAGE}/tests/test_build_transfer.py",
    ]


def verify_archive(path, manifest):
    with ZipFile(path) as archive:
        expected = set(manifest["files"]) | {"transfer-manifest.json"}
        names = archive.namelist()
        if len(names) != len(expected) or set(names) != expected:
            raise ValueError("Archive file closure mismatch")
        if json.loads(archive.read("transfer-manifest.json")) != manifest:
            raise ValueError("Archive manifest mismatch")
        for name, checksum in manifest["files"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != checksum:
                raise ValueError("Archive checksum mismatch: " + name)


def build(output):
    root = Path(__file__).resolve().parents[4]
    output = Path(output)
    contents = {name: (root / name).read_bytes() for name in PATHS}
    manifest = {
        "format": "repository-adoption-transfer/v1",
        "artifact_type": "agent-adoption-kit",
        "kit_version": "1.2",
        "entrypoint": "docs/portable-repository-adoption.md",
        "files": {name: hashlib.sha256(data).hexdigest()
                  for name, data in contents.items()},
    }
    # A hard link publishes complete bytes atomically without replacing a target.
    # On filesystems without hard links, fail without publishing a partial ZIP.
    with tempfile.TemporaryDirectory(prefix=".adoption-build-", dir=output.parent) as temporary:
        candidate = Path(temporary) / "candidate.zip"
        with ZipFile(candidate, "x", compression=ZIP_DEFLATED) as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
            archive.writestr("transfer-manifest.json", json.dumps(manifest, indent=2) + "\n")
        verify_archive(candidate, manifest)
        os.link(candidate, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
