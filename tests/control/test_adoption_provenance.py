#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise behavioral compatibility and integrity of optional invocation receipts."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/control/reasoning-log-schema-guardian/scripts"))
import adoption_provenance as receipts  # noqa: E402 - direct-script path setup above


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = {"skill_id": "validator", "operation_id": "check", "attempt": 1}

    def record(self, operation=lambda: {"ok": True}):
        return receipts.invoke_recorded(operation, self.metadata, self.root)

    def only(self):
        return next(self.root.iterdir())

    def test_preserves_identity_and_snapshots(self):
        result = {"items": [1]}

        def operation():
            self.metadata["attempt"] = 2
            return result

        self.assertIs(self.record(operation), result)
        result["items"].append(2)
        provenance = receipts.validate_invocation(self.only())
        terminal = json.loads((self.only() / "result.json").read_text())
        self.assertEqual(provenance["metadata"]["attempt"], 1)
        self.assertEqual(terminal["result"], {"items": [1]})

    def test_canonical_json_rejects_lossy_values(self):
        self.assertEqual(
            receipts.canonical_digest({"b": 1, "a": 2}),
            receipts.canonical_digest({"a": 2, "b": 1}),
        )
        for value in (float("nan"), float("inf"), {1: "x"}, (1, 2), {1, 2}, object()):
            with (
                self.subTest(value=type(value).__name__),
                self.assertRaises((ValueError, TypeError)),
            ):
                receipts.canonical_digest(value)

    def test_original_failure_and_cancellation(self):
        for error in (
            RuntimeError("private secret"),
            KeyboardInterrupt("private secret"),
        ):
            with tempfile.TemporaryDirectory() as temp:

                def operation():
                    raise error

                with self.assertRaises(type(error)) as raised:
                    receipts.invoke_recorded(operation, self.metadata, temp)
                self.assertIs(raised.exception, error)
                directory = next(Path(temp).iterdir())
                provenance = receipts.validate_invocation(directory)
                self.assertEqual(
                    provenance["status"],
                    "failed" if isinstance(error, Exception) else "cancelled",
                )
                for path in directory.iterdir():
                    self.assertNotIn("private secret", path.read_text())

    def test_sink_failure_never_retries_or_replaces_outcomes(self):
        called = []
        sentinel = object()
        with patch.object(
            receipts, "append_skill_start", side_effect=OSError("private secret")
        ):
            with warnings.catch_warnings(record=True) as emitted:
                self.assertIs(
                    self.record(lambda: called.append(1) or sentinel), sentinel
                )
            self.assertEqual(len(called), 1)
            self.assertEqual(len(emitted), 1)
            self.assertNotIn("private secret", str(emitted[0].message))
        error = RuntimeError("operation failed")
        with patch.object(receipts, "_write", side_effect=OSError("sink failed")):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                with self.assertRaises(RuntimeError) as raised:
                    self.record(lambda: (_ for _ in ()).throw(error))
                self.assertIs(raised.exception, error)

    def test_unsupported_json_returns_unchanged(self):
        sentinel = object()
        with self.assertWarns(RuntimeWarning):
            self.assertIs(self.record(lambda: sentinel), sentinel)
        self.assertFalse((self.only() / "provenance.json").exists())

    def test_unknown_metadata_does_not_log_raw_inputs(self):
        self.metadata["raw_input"] = "private secret"
        with self.assertWarns(RuntimeWarning):
            self.assertEqual(self.record(lambda: 17), 17)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_nested_and_concurrent_invocations(self):
        def parent():
            return self.record(lambda: {"ok": "child"})

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.record(parent), range(8)))
        records = [receipts.validate_invocation(path) for path in self.root.iterdir()]
        self.assertEqual(len(records), 16)
        ids = {record["invocation_id"] for record in records}
        self.assertEqual(len(ids), 16)
        parents = [
            record for record in records if record["parent_invocation_id"] is None
        ]
        self.assertEqual(len(parents), 8)
        for parent_record in parents:
            self.assertEqual(
                sum(
                    record["parent_invocation_id"] == parent_record["invocation_id"]
                    for record in records
                ),
                1,
            )

    def test_caller_retry_is_new_attempt(self):
        calls = []

        def operation():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("first attempt")
            return True

        with self.assertRaises(RuntimeError):
            self.record(operation)
        self.metadata["attempt"] = 2
        self.assertTrue(self.record(operation))
        records = [receipts.validate_invocation(path) for path in self.root.iterdir()]
        self.assertEqual({record["metadata"]["attempt"] for record in records}, {1, 2})
        self.assertEqual(len(calls), 2)

    def test_tampering_and_cross_invocation_join(self):
        self.record()
        first = self.only()
        self.record()
        second = next(path for path in self.root.iterdir() if path != first)
        (first / "result.json").write_bytes((second / "result.json").read_bytes())
        with self.assertRaises(ValueError):
            receipts.validate_invocation(first)
        # Even when the substituted log digest is recomputed, its identity fails.
        (second / "reasoning.jsonl").write_bytes(
            (first / "reasoning.jsonl").read_bytes()
        )
        provenance = json.loads((second / "provenance.json").read_text())
        provenance["reasoning_digest"] = hashlib.sha256(
            (second / "reasoning.jsonl").read_bytes()
        ).hexdigest()
        (second / "provenance.json").write_text(json.dumps(provenance))
        with self.assertRaises(ValueError):
            receipts.validate_invocation(second)

    def test_render_is_offline_escaped_and_preserves_bytes(self):
        self.metadata["skill_id"] = '<script>alert("x")</script>'
        self.record()
        directory = self.only()
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        with patch.object(
            receipts, "invoke_recorded", side_effect=AssertionError("must not execute")
        ):
            rendered = receipts.render_summary(directory)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertEqual(
            before, {path.name: path.read_bytes() for path in directory.iterdir()}
        )

    def test_disabled_is_transparent(self):
        self.assertEqual(
            receipts.invoke_recorded(lambda: 3, {"raw": object()}, None), 3
        )
        self.assertEqual(list(self.root.iterdir()), [])


class ReceiptCursor:
    """Shared finite suite cursor; unittest owns fixtures, assertions and cleanup."""

    def __init__(self, result, cases=None):
        self.cases = list(
            cases
            if cases is not None
            else unittest.defaultTestLoader.loadTestsFromTestCase(ReceiptTests)
        )
        self.result = result
        self.index = 0
        self.pending = None

    def state(self):
        return {
            "index": self.index,
            "tests": [case._testMethodName for case in self.cases],
            "tests_run": self.result.testsRun,
            "failures": len(self.result.failures),
            "errors": len(self.result.errors),
        }

    def run_case(self):
        if self.pending is not None or self.index >= len(self.cases):
            raise ValueError("case already run or suite complete")
        failures, errors = len(self.result.failures), len(self.result.errors)
        # Delegate the actual call and all fixture handling to native unittest.
        unittest.TestSuite([self.cases[self.index]]).run(self.result)
        diagnostics = [
            text
            for _, text in self.result.failures[failures:] + self.result.errors[errors:]
        ]
        status = (
            "error"
            if len(self.result.errors) > errors
            else "failure" if len(self.result.failures) > failures else "passed"
        )
        self.pending = {"status": status, "diagnostics": diagnostics}
        return self.pending

    def advance(self, observation):
        if self.pending is None or observation != self.pending:
            raise ValueError("missing or mismatched case observation")
        self.index += 1
        self.pending = None
        return self.index == len(self.cases)


class ReceiptSuite(unittest.TestSuite):
    """One runner and result in both native CLI and staged subprocess mode."""

    def run(self, result, debug=False):
        cursor = ReceiptCursor(result, list(self))
        if debug:
            return super().run(result, debug=True)
        while cursor.index < len(cursor.cases) and not result.shouldStop:
            cursor.advance(cursor.run_case())
        return result


def load_tests(loader, tests, pattern):
    return ReceiptSuite(loader.loadTestsFromTestCase(ReceiptTests))


def protocol_main():
    """Private line protocol: the hub still owns one real subprocess boundary."""
    import contextlib
    import io

    output = sys.stdout
    captured = io.StringIO()

    def send(value):
        output.write(json.dumps(value) + "\n")
        output.flush()

    class ProtocolSuite(ReceiptSuite):
        def run(self, result, debug=False):
            cursor = ReceiptCursor(result)
            send({"state": cursor.state()})
            for line in sys.stdin:
                command = json.loads(line)
                if command["operation"] == "run_case":
                    send({"observation": cursor.run_case()})
                elif command["operation"] == "advance":
                    done = cursor.advance(command["observation"])
                    send({"state": cursor.state(), "done": done})
                    if done:
                        return result
                else:
                    raise ValueError("unknown protocol operation")
            raise EOFError("suite interrupted before completion")

    with contextlib.redirect_stdout(captured):
        result = unittest.TextTestRunner().run(ProtocolSuite())
    send({"stdout": captured.getvalue(), "ok": result.wasSuccessful()})
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--workflow-protocol"]:
        raise SystemExit(protocol_main())
    unittest.main()
