# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic provider and compiler boundaries for the real source-grounded workflow."""

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import json
import importlib.util
import io
import sys
import shutil
import subprocess
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr

CODE = "theorem fixture : True := by trivial"
GOOD = """import Mathlib.Data.Nat.Basic

/--
Original source (NL): Adding zero preserves a natural number.
Original source (LaTeX): `n + 0 = n` for every natural number n.
Mathlib grounding: Nat.add_zero.
-/
theorem add_zero_identity (n : Nat) : n + 0 = n := by
  exact Nat.add_zero n
"""
SOURCE_ROOT = Path(__file__).resolve().parents[3]


def install(module, directory, mode):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    calls = []
    real_run = subprocess.run
    concept_compiles = 0

    def log(kind, payload):
        row = {"kind": kind, "payload": payload}
        calls.append(row)
        with (directory / "calls.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")

    class Provider:
        name = "deterministic-readiness-fixture"
        client = SimpleNamespace(close=lambda: None)

        def __init__(self, kind=None):
            self.kind = kind

        def generate(self, messages):
            system = messages[0]["content"]
            kind = self.kind
            if kind is None:
                if "Aspect name: latex_expansion_completeness" in system:
                    kind = "completeness"
                elif (
                    "Aspect name: latex_expansion_bindings" in system
                    or "Aspect name: latex_expansion_binding" in system
                ):
                    kind = "bindings"
                elif "pre-formalization expansions" in system:
                    kind = "expand"
                elif "classify the refinement transition" in system:
                    kind = "taxonomy"
                elif "evaluate a specific aspect" in system:
                    kind = "soft"
                elif "make it syntactically correct" in system:
                    kind = "formal"
                elif "make it satisfy a specific aspect" in system:
                    kind = "semantic"
                else:
                    kind = "draft"
            log(kind, messages)
            if mode == kind + "_failure":
                raise TimeoutError("fixture provider failure: " + kind)
            if kind == "expand":
                return (
                    "%%%%%%%%%%\n"
                    + (
                        ""
                        if mode == "empty"
                        else "Expanded proposition with explicit assumptions."
                    )
                    + "\n%%%%%%%%%%"
                )
            if kind in {"completeness", "bindings", "soft"}:
                return "Explanation: fixture judgment\nJudgement: " + (
                    "False"
                    if (mode == "review_false" and kind == "completeness")
                    or (
                        mode == "semantic"
                        and kind == "soft"
                        and not any(r["kind"] == "semantic" for r in calls)
                    )
                    else "True"
                )
            if kind == "taxonomy":
                return "{}"
            broken = mode in {"refine", "refinement_cap", "semantic"} and (
                kind == "draft" or mode == "refinement_cap"
            )
            return (
                "%%%%%%%%%%\n"
                + ("-- broken\n" if broken else "")
                + (GOOD if mode == "consistent" else CODE)
                + "\n%%%%%%%%%%"
            )

    def compiler(command, **kwargs):
        nonlocal concept_compiles
        if command[0] == "rg":
            return real_run(command, **kwargs)
        if len(command) > 1 and str(command[1]).endswith(".py"):
            # Execute source-owned reporting CLIs in-process. A disposable copy
            # gives their __file__-relative artifact defaults an isolated root.
            # No Python report implementation or result is substituted.
            mirror = directory / "source"
            if not mirror.exists():
                for source in (SOURCE_ROOT / "skills").glob("**/scripts/*.py"):
                    target = mirror / source.relative_to(SOURCE_ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            path = Path(command[1])
            if not path.is_absolute():
                path = (Path(kwargs.get("cwd", directory)) / path).resolve()
            if path.is_relative_to(SOURCE_ROOT):
                path = mirror / path.relative_to(SOURCE_ROOT)
            assert path.is_relative_to(mirror), command
            log("python_cli", {"script": path.name, "arguments": command[2:]})
            name = "readiness_fixture_" + str(abs(hash(str(path))))
            spec = importlib.util.spec_from_file_location(name, path)
            native = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = native
            spec.loader.exec_module(native)
            previous = sys.argv
            stdout, stderr = io.StringIO(), io.StringIO()
            try:
                sys.argv = [str(path), *command[2:]]
                with (
                    patch("subprocess.run", compiler),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    status = native.main()
            finally:
                sys.argv = previous
            return SimpleNamespace(
                returncode=status, stdout=stdout.getvalue(), stderr=stderr.getvalue()
            )
        assert list(command[1:3]) == ["env", "lean"], command
        if command[0] == "fixture-lake":
            assert kwargs["timeout"] == 13
        code = Path(command[-1]).read_text()
        log("compile", {"code": code, "file_prefix": Path(command[-1]).stem})
        if mode == "compiler_failure":
            raise OSError("fixture compiler launch failure")
        if "#check " in code:
            concept_compiles += 1
            if mode in {"concept_error", "concept_later_error"} and (
                mode == "concept_error" or concept_compiles == 2
            ):
                raise OSError("fixture concept compiler error")
            success = mode not in {
                "concept_cap",
                "concept_widen",
                "concept_later_error",
            } or concept_compiles >= (2 if mode == "concept_widen" else 99)
            errors = "\n".join(
                f"{command[-1]}:{i}:1: error: rejected {line[7:]}"
                for i, line in enumerate(code.splitlines(), 1)
                if line.startswith("#check ")
            )
            return SimpleNamespace(
                returncode=int(not success), stdout="" if success else errors, stderr=""
            )
        failed = "-- broken" in code
        return SimpleNamespace(
            returncode=int(failed),
            stdout="error: fixture syntax" if failed else "",
            stderr="",
        )

    module.subprocess = SimpleNamespace(
        run=compiler,
        TimeoutExpired=subprocess.TimeoutExpired,
        CalledProcessError=subprocess.CalledProcessError,
    )
    module._augment_env_with_lean_path = lambda: {}

    @contextmanager
    def factory(request):
        context = request["agent_configuration"]
        agent = module.IterativeSelfRefinementAgentC(
            autoformalizer=module.AutoformalizationAgent(
                llm=Provider("draft"), formal_language="Lean4"
            ),
            hard_critique=module.HardCritiqueAgent(
                formal_language="Lean4",
                file_dir=str(directory),
                lean_workdir=str(directory),
                lake_bin="fixture-lake",
                lean_timeout_seconds=13,
            ),
            soft_critique=module.SoftCritiqueAgent(
                llm=Provider("soft"),
                formal_language="Lean4",
                aspect_description=context["aspect_description"],
            ),
            formal_refiner=module.FormalRefinementAgent(
                llm=Provider("formal"), formal_language="Lean4"
            ),
            informal_refiner=module.InformalRefinementAgent(
                llm=Provider("semantic"), formal_language="Lean4"
            ),
            refinement_taxonomy_agent=module.RefinementTaxonomyAgent(
                llm=Provider("taxonomy"), formal_language="Lean4"
            ),
            aspect_description=context["aspect_description"],
            max_iterations=context.get("max_iterations", 4),
            default_target_compatibility_score=context.get(
                "default_target_compatibility_score", 100
            ),
        )
        for key, cls, kind in [
            ("latex_expander", module.LatexExpansionAgent, "expand"),
            (
                "latex_expansion_completeness_reviewer",
                module.LatexExpansionCompletenessReviewAgent,
                "completeness",
            ),
            (
                "latex_expansion_binding_reviewer",
                module.LatexExpansionBindingReviewAgent,
                "bindings",
            ),
        ]:
            setattr(
                agent, key, cls(llm=Provider(kind)) if context.get(key, False) else None
            )
        if not context.get("refinement", True):
            agent.soft_critique = agent.formal_refiner = agent.informal_refiner = None
        yield agent

    factory.Provider = Provider
    return factory, calls


def serve(directory, mode):
    import mcp_server
    import agentc_workflow_tools as tools

    factory, _ = install(tools.agentc_module(), directory, mode)
    tools.ServiceLLM = lambda config: factory.Provider()
    settings = {
        ("lean", "workdir"): directory,
        ("lean", "lake_bin"): "fixture-lake",
        ("lean", "lean_timeout_seconds"): 13,
        ("paths", "artifacts_dir"): directory,
    }
    mcp_server._AGENTC_SERVICE_CONFIG = SimpleNamespace(
        get=lambda section, key: settings[(section, key)]
    )
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(directory).resolve()]
    mcp_server.CALL_LOG_PATH = Path(directory) / "server-calls.jsonl"
    mcp_server.mcp.run(transport="stdio")
