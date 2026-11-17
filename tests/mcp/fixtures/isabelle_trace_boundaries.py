# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external provider and Isabelle process boundaries for tests.

The compiler fixture resolves /package into an isolated export snapshot, then
uses the actual PRISM parser, checker, compiler, runtime and Lunar observers.
It does not replace reasoning steps or fabricate completion events/receipts.
"""

from tempfile import gettempdir

from pathlib import Path
import json
import subprocess
from types import SimpleNamespace

from prism.language import parse_source, check, elaborate, compile as compile_program
from prism.runtime import CompositeEffectHandler, FileArtifactStore
from prism.sdk import WorkspaceModuleLoader
from domain_packages.worker.prism import (
    VariantModelHandler,
    ObservedHandler,
    ObservedRecorder,
    run_with_reasoning,
)

THEORY = 'theory Mathformer\nimports Complex_Main\nbegin\nlemma mathformer_target: "(x::real) = x" by simp\nend\n'


class Boundaries:
    def __init__(self, package, options=None):
        self.package = Path(package)
        self.options = options or {}
        self.events = []
        self.model_calls = []
        self.executions = []
        self.processes = []
        self.killed = []
        self.clock = 0

    def event(self, kind, payload):
        self.events.append((kind, payload))

    def completion(self, **arguments):
        schema = arguments["response_format"]["json_schema"]["schema"]
        self.model_calls.append(arguments)
        is_repair = "code" in schema.get("properties", {})
        if self.options.get("provider_error") or (
            is_repair and self.options.get("repair_error")
        ):
            raise RuntimeError("fixture provider failure")

        def value(s, name=""):
            if "enum" in s:
                return s["enum"][0]
            if "anyOf" in s:
                return value(s["anyOf"][0], name)
            kind = s.get("type")
            if kind == "object":
                return {k: value(v, k) for k, v in s.get("properties", {}).items()}
            if kind == "array":
                if name == "candidate_artifacts":
                    return ["no theory"] if self.options.get("no_theory") else [THEORY]
                return [value(s.get("items", {"type": "string"}), name)]
            if kind == "boolean":
                return True
            if kind in ("number", "integer"):
                return 1
            if name == "code":
                return (
                    THEORY.replace("by simp", "sorry")
                    if self.options.get("reject_repair")
                    else THEORY + "\n"
                )
            return "deterministic fixture evidence"

        return {"choices": [{"message": {"content": json.dumps(value(schema))}}]}

    def execute_prism(
        self,
        *,
        source,
        entry_argument,
        prepared_input,
        selected_model,
        artifact_root,
        completion,
        on_reasoning,
        effect_handler=None,
    ):
        relative = Path(source).relative_to(
            str(Path(gettempdir()) / "mathformer-test-fixtures/package")
        )
        path = self.package / relative
        self.executions.append(
            {
                "source": relative.as_posix(),
                "entry_argument": entry_argument,
                "input": prepared_input,
            }
        )
        parsed = parse_source(path.read_text(), path=str(path))
        program = compile_program(
            elaborate(
                check(parsed, modules=WorkspaceModuleLoader(project_root=path.parent))
            )
        )
        calls = {}
        recorder = ObservedRecorder(
            FileArtifactStore(Path(artifact_root) / "prism-effects"),
            on_reasoning,
            calls,
        )
        handler = VariantModelHandler(
            program,
            ObservedHandler(
                model="fixture/deterministic",
                completion=completion,
                callback=on_reasoning,
                model_calls=calls,
            ),
        )
        if effect_handler is not None:
            handler = CompositeEffectHandler((effect_handler, handler))
        output = run_with_reasoning(
            program,
            callback=on_reasoning,
            handler=handler,
            effect_recorder=recorder,
            entry_arguments={entry_argument: prepared_input["value"]},
        )
        return SimpleNamespace(
            status=output.status, typed_result=output.result, run_output=output
        )

    def which(self, name):
        assert name == "isabelle"
        return (
            None
            if self.options.get("missing")
            else str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/isabelle")
        )

    def popen(self, argv, **kw):
        assert argv[0] == str(
            Path(gettempdir()) / "mathformer-test-fixtures/fixture/isabelle"
        )
        assert kw["start_new_session"]
        directory = Path(kw["cwd"])
        version = argv[1] == "version"
        if version:
            kw["stdout"].write("Isabelle fixture version\n")
        else:
            assert (directory / "Mathformer.thy").is_file()
            assert (directory / "ROOT").read_text().startswith("session Mathformer_Run")
            kw["stderr"].write("fixture compiler diagnostic\n")
        row = dict(
            argv=argv, directory=directory, version=version, waits=[], env=kw.get("env")
        )
        self.processes.append(row)
        outcomes = self.options.get("outcomes", [0])
        index = (
            int(directory.name.removeprefix("attempt-"))
            if directory.name.startswith("attempt-")
            else 1
        )
        outcome = 0 if version else outcomes[min(index - 1, len(outcomes) - 1)]
        if version and self.options.get("version_failure"):
            outcome = 1

        def wait(timeout=None):
            row["waits"].append(timeout)
            if outcome == "timeout" and timeout is not None:
                raise subprocess.TimeoutExpired(argv, timeout)
            return -9 if outcome == "timeout" else outcome

        return SimpleNamespace(pid=78231, wait=wait)

    def install(self, runtime):
        loader = runtime._isabelle_module

        def native():
            module = loader()
            module.shutil = SimpleNamespace(which=self.which)
            module.subprocess = SimpleNamespace(
                Popen=self.popen, TimeoutExpired=subprocess.TimeoutExpired
            )
            module.os = SimpleNamespace(
                environ={}, killpg=lambda pid, sig: self.killed.append((pid, sig))
            )
            module.time = SimpleNamespace(monotonic=self.tick)
            return module

        runtime._isabelle_module = native

    def tick(self):
        self.clock += 1
        return self.clock

    def services(self):
        return SimpleNamespace(
            model=SimpleNamespace(provider="fixture", model_id="deterministic"),
            completion=self.completion,
            event=self.event,
            execute_prism=self.execute_prism,
        )
