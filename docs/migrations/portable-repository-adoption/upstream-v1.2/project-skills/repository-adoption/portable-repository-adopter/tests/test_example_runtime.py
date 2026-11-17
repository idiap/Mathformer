# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Run with unittest discovery; requires only Python's standard library."""
import importlib.util
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "example_runtime.py"
SPEC = importlib.util.spec_from_file_location("example_runtime", SOURCE)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class AdoptionExampleTests(unittest.TestCase):
    def context(self, emit, diagnostic=lambda message: None):
        return {"identity": {"run_id": "test-run", "invocation_id": "test-1"},
                "emit": emit, "diagnostic": diagnostic}

    def test_registered_route_calls_once_and_emits_once(self):
        for config in ({"timeout": 10}, {"timeout": 0}, {"timeout": -1, "extra": 1}):
            with self.subTest(config=config):
                expected = runtime.validate(config)
                events = []
                with patch.object(runtime, "validate", wraps=runtime.validate) as implementation:
                    result = runtime.REGISTRY[runtime.SKILL["binding"]](config, context=self.context(events.append))
                self.assertEqual(result, expected)
                implementation.assert_called_once_with(config)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["execution_status"], "completed")

    def test_legacy_error_preserved_and_recorded(self):
        events = []
        with self.assertRaises(KeyError) as error:
            runtime.invoke_validate({}, context=self.context(events.append))
        self.assertEqual(error.exception.args, ("timeout",))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["execution_status"], "failed")
        self.assertEqual(events[0]["error_type"], "KeyError")

    def test_sink_and_diagnostic_failures_preserve_result_and_exception(self):
        def unavailable(value):
            raise OSError("fixture failure")
        context = self.context(unavailable, unavailable)
        self.assertEqual(runtime.invoke_validate({"timeout": 0}, context=context),
                         ["timeout must be positive"])
        error = KeyError("original")
        with patch.object(runtime, "validate", side_effect=error):
            with self.assertRaises(KeyError) as raised:
                runtime.invoke_validate({}, context=context)
        self.assertIs(raised.exception, error)
        self.assertEqual(runtime.invoke_validate({"timeout": 10}, context={"identity": {}}), [])

    def test_two_invocations_have_distinct_identities_and_bound_results(self):
        with tempfile.TemporaryDirectory() as directory:
            roots = [Path(directory) / name for name in ("first", "second")]
            first, second = [runtime.build_example(root) for root in roots]
            for key in ("run_id", "invocation_id"):
                self.assertNotEqual(first[key], second[key])
            self.assertNotEqual(first["entries"][0]["event_key"], second["entries"][0]["event_key"])
            self.assertEqual(first["skill_metadata"], second["skill_metadata"])
            self.assertNotEqual(first["terminal_snapshot"]["result_byte_sha256"],
                                second["terminal_snapshot"]["result_byte_sha256"])
            for record, root in zip((first, second), roots):
                runtime.verify(record, root)
                self.assertEqual(json.loads((root / "findings.json").read_bytes())["findings"],
                                 ["timeout must be positive"])
            for part, error in (("entries", "Invocation join"),
                                ("provenance", "Invocation join"),
                                ("terminal_snapshot", "Terminal snapshot join")):
                with self.subTest(part=part):
                    mixed = copy.deepcopy(first)
                    mixed[part] = second[part]
                    mixed["digest"] = runtime.digest(mixed)
                    with self.assertRaisesRegex(ValueError, error):
                        runtime.verify(mixed, roots[0])

    def test_cross_run_result_substitution_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            first_root, second_root = Path(directory) / "first", Path(directory) / "second"
            first, second = runtime.build_example(first_root), runtime.build_example(second_root)
            (first_root / "findings.json").write_bytes((second_root / "findings.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "Artifact digest"):
                runtime.verify(first, first_root)
            # Updating the artifact hash alone must not detach the terminal snapshot.
            first["artifacts"][1]["byte_sha256"] = second["artifacts"][1]["byte_sha256"]
            first["digest"] = runtime.digest(first)
            with self.assertRaisesRegex(ValueError, "Terminal result digest"):
                runtime.verify(first, first_root)
            # Even after rehashing both links, the result belongs to another invocation.
            first["terminal_snapshot"]["result_byte_sha256"] = second["terminal_snapshot"]["result_byte_sha256"]
            first["digest"] = runtime.digest(first)
            with self.assertRaisesRegex(ValueError, "Result invocation join"):
                runtime.verify(first, first_root)

    def test_unsupported_schema_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            record = runtime.build_example(root)
            self.assertEqual(record["schema_version"], "repository-adoption.example/v2")
            record["schema_version"] = "repository-adoption.example/v1"
            record["digest"] = runtime.digest(record)
            with self.assertRaisesRegex(ValueError, "Unsupported fixture schema"):
                runtime.verify(record, root)

    def test_artifacts_digests_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            record = runtime.build_example(root)
            self.assertEqual(json.loads((root / "trace.json").read_bytes()), record)
            runtime.verify(record, root)
            with self.assertRaises(FileExistsError):
                runtime.build_example(root)
            record["summary"] = "tampered"
            with self.assertRaisesRegex(ValueError, "Record digest"):
                runtime.verify(record, root)
            record["digest"] = runtime.digest(record)
            (root / "findings.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Artifact digest"):
                runtime.verify(record, root)

    def test_frozen_metadata_escape_and_join(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            record = runtime.build_example(root)
            record["skill_metadata"]["label"] = '<script>alert("x")</script>'
            page = runtime.render(record)
            self.assertNotIn("<script>", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertLess(page.index("Check configuration"), page.index("Reasoning type:"))
            self.assertIn("One configuration finding returned.", page)
            self.assertIn("Rationale not recorded.", page)
            record["skill_metadata"]["digest"] = runtime.digest(record["skill_metadata"])
            record["provenance"][0]["id"] = "wrong-invocation"
            record["digest"] = runtime.digest(record)
            with self.assertRaisesRegex(ValueError, "Invocation join"):
                runtime.verify(record, root)


if __name__ == "__main__":
    unittest.main()
