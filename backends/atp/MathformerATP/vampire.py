# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Bridge informal theorem statements and first-order automated theorem proving in a traceable way.
#
# Intent:
#   Represent ATP candidates, premise-selection evidence, Vampire execution, and proof artifacts as explicit data.
#
# Function:
#   Defines the proof-search machinery used by examples, tests, and theorem-discovery workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Clear TPTP/Vampire interface for Mathformer ATP proof search."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Generator, Sequence

from .generation import build_generation_report, generate_candidate_lemmas
from .premises import (
    PremiseCandidate,
    build_premise_registry,
    select_premises,
    selected_candidates,
)

PROOF_STATUSES = {"Theorem", "Unsatisfiable", "ContradictoryAxioms"}
COUNTERMODEL_STATUSES = {"CounterSatisfiable", "Satisfiable", "FiniteModel"}


def now() -> str:
    """Document the responsibility of ``now``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def _comment(text: str) -> str:
    """Document the responsibility of ``_comment``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return "\n".join(f"% {line}" if line else "%" for line in text.splitlines())


@dataclass(frozen=True)
class TPTPFormula:
    """One TPTP formula."""

    name: str
    role: str
    formula: str
    language: str = "fof"

    def render(self) -> str:
        """Document the responsibility of ``TPTPFormula.render``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Render structured information into a human-readable or machine-consumable representation.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return f"{self.language}({self.name},{self.role},\n  {self.formula})."


@dataclass
class ATPProblem:
    """A first-order ATP problem with informal provenance."""

    problem_id: str
    formulas: list[TPTPFormula]
    informal_statement: str = ""
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_tptp(self) -> str:
        """Document the responsibility of ``ATPProblem.to_tptp``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``ATPProblem.to_tptp`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        header = {
            "problem_id": self.problem_id,
            "generated_at": now(),
            "source_url": self.source_url,
            **self.metadata,
        }
        lines = [
            _comment("Mathformer ATP problem"),
            _comment(json.dumps(header, ensure_ascii=False, sort_keys=True)),
        ]
        if self.informal_statement:
            lines.append(_comment("Informal statement:"))
            lines.append(_comment(self.informal_statement))
        lines.extend(formula.render() for formula in self.formulas)
        return "\n\n".join(lines) + "\n"

    def write(self, path: Path) -> Path:
        """Document the responsibility of ``ATPProblem.write``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Persist or emit computed data in the format expected by later workflow stages.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_tptp(), encoding="utf-8")
        return path

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``ATPProblem.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``ATPProblem.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "problem_id": self.problem_id,
            "informal_statement": self.informal_statement,
            "source_url": self.source_url,
            "metadata": self.metadata,
            "formulas": [asdict(formula) for formula in self.formulas],
        }


@dataclass
class InformalProof:
    """Human-readable proof explanation derived from a Vampire result."""

    ok: bool
    style: str
    problem_id: str
    status: str | None
    statement: str
    source_url: str | None
    formal_step_count: int
    steps: list[str]
    text: str
    generated_at: str = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``InformalProof.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``InformalProof.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return asdict(self)


@dataclass
class ATPResult:
    """Structured Vampire execution result."""

    ok: bool
    proof_found: bool
    status: str | None
    problem_path: str
    command: list[str]
    returncode: int
    elapsed_seconds: float
    stdout: str
    stderr: str
    proof: str
    formal_proof: str = ""
    informal_proof: InformalProof | None = None
    generated_at: str = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``ATPResult.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``ATPResult.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return asdict(self)

    def write_json(self, path: Path) -> Path:
        """Document the responsibility of ``ATPResult.write_json``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Persist or emit computed data in the format expected by later workflow stages.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path


def parse_szs_status(output: str) -> str | None:
    """Document the responsibility of ``parse_szs_status``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.search(r"%\s*SZS status\s+([A-Za-z_][A-Za-z0-9_]*)\b", output)
    return match.group(1) if match else None


def parse_tstp_proof(output: str) -> str:
    """Document the responsibility of ``parse_tstp_proof``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.search(
        r"%\s*SZS output start Proof.*?\n(?P<proof>.*?)%\s*SZS output end Proof",
        output,
        flags=re.DOTALL,
    )
    return match.group("proof").strip() if match else ""


def _canonical_phrase(text: str) -> str:
    """Document the responsibility of ``_canonical_phrase``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_canonical_phrase`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return re.sub(r"^(?:a|an|the)\s+", "", cleaned)


def _predicate_name(text: str) -> str:
    """Document the responsibility of ``_predicate_name``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_predicate_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    name = re.sub(r"[^a-z0-9]+", "_", _canonical_phrase(text)).strip("_")
    if not name:
        return "predicate"
    if not name[0].isalpha():
        return f"p_{name}"
    return name


def _parse_unary_implication_chain(
    informal_statement: str,
) -> tuple[str, str, str] | None:
    """Document the responsibility of ``_parse_unary_implication_chain``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.search(
        r"\b(?:every|all)\s+(?P<start>[^.]+?)\s+(?:is|are)\s+(?:(?:a|an|the)\s+)?(?P<middle>[^.]+?)\.\s*"
        r"(?:every|all)\s+(?P<middle2>[^.]+?)\s+(?:is|are)\s+(?:(?:a|an|the)\s+)?(?P<end>[^.]+?)\.\s*"
        r"(?:therefore|so|hence),?\s+(?:every|all)\s+(?P<goal_start>[^.]+?)\s+"
        r"(?:is|are)\s+(?:(?:a|an|the)\s+)?(?P<goal_end>[^.]+?)(?:\.|$)",
        informal_statement,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    start = _canonical_phrase(match.group("start"))
    middle = _canonical_phrase(match.group("middle"))
    middle2 = _canonical_phrase(match.group("middle2"))
    end = _canonical_phrase(match.group("end"))
    goal_start = _canonical_phrase(match.group("goal_start"))
    goal_end = _canonical_phrase(match.group("goal_end"))
    if start != goal_start or middle != middle2 or end != goal_end:
        return None
    return start, middle, end


def count_tstp_steps(proof: str) -> int:
    """Document the responsibility of ``count_tstp_steps``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``count_tstp_steps`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return len(re.findall(r"^\s*(?:fof|cnf)\(", proof, flags=re.MULTILINE))


def _generic_formula_steps(problem: ATPProblem) -> list[str]:
    """Document the responsibility of ``_generic_formula_steps``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_generic_formula_steps`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    axioms = [formula.name for formula in problem.formulas if formula.role == "axiom"]
    conjectures = [
        formula.name for formula in problem.formulas if formula.role == "conjecture"
    ]
    steps = []
    if axioms:
        steps.append(f"Use the axioms named {', '.join(axioms)}.")
    if conjectures:
        steps.append(
            f"Negate the conjecture named {', '.join(conjectures)} and search for a contradiction."
        )
    steps.append(
        "Vampire clausifies the first-order formulas and performs resolution-style proof search."
    )
    steps.append(
        "The TSTP proof reaches a contradiction, so the conjecture follows from the axioms."
    )
    return steps


def _informal_steps(problem: ATPProblem | None) -> list[str]:
    """Document the responsibility of ``_informal_steps``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_informal_steps`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if problem and problem.problem_id == "subset_relation_is_transitive":
        return [
            "Assume subset(r,s) and subset(s,t).",
            "Take an arbitrary object x and assume member(x,r).",
            "By the definition of subset and subset(r,s), member(x,s).",
            "By the definition of subset and subset(s,t), member(x,t).",
            "Since x was arbitrary, every member of r is a member of t.",
            "By the definition of subset, subset(r,t).",
            "Vampire's formal TSTP proof refutes the negation of subset(r,t) and derives $false.",
        ]
    if problem and problem.problem_id == "subset_relation_membership_chain":
        return [
            "Assume every member of r is a member of s.",
            "Assume every member of s is a member of t.",
            "Take an arbitrary object x and assume member(x,r).",
            "The first assumption gives member(x,s).",
            "The second assumption then gives member(x,t).",
            "Since x was arbitrary, every member of r is a member of t.",
            "Vampire confirms this by deriving a contradiction from the negated conjecture.",
        ]
    if (
        problem
        and problem.metadata.get("autoformalization_strategy")
        == "unary predicate implication chain"
    ):
        start = problem.metadata["start_label"]
        middle = problem.metadata["middle_label"]
        end = problem.metadata["end_label"]
        return [
            f"Assume an arbitrary object x satisfies the description '{start}'.",
            f"The first premise says anything satisfying '{start}' also satisfies '{middle}', so x satisfies '{middle}'.",
            f"The second premise says anything satisfying '{middle}' also satisfies '{end}', so x satisfies '{end}'.",
            f"Since x was arbitrary, everything satisfying '{start}' also satisfies '{end}'.",
            "Vampire's formal TSTP proof verifies this by refuting the negated conjecture and deriving $false.",
        ]
    if (
        problem
        and problem.metadata.get("autoformalization_strategy")
        == "transitive irreflexive relation asymmetry"
    ):
        relation = problem.metadata["relation_predicate"]
        return [
            f"Take arbitrary objects x and y and assume {relation}(x,y).",
            f"To prove asymmetry, suppose for contradiction that {relation}(y,x).",
            f"By transitivity, {relation}(x,y) and {relation}(y,x) imply {relation}(x,x).",
            f"Irreflexivity says {relation}(x,x) is impossible.",
            f"Therefore {relation}(y,x) cannot hold whenever {relation}(x,y) holds.",
            "Since x and y were arbitrary, the relation is asymmetric.",
            "Vampire's formal TSTP proof proves the universal implication by refuting its negation and deriving $false.",
        ]
    if (
        problem
        and problem.metadata.get("autoformalization_strategy")
        == "group inverse product theorem"
    ):
        steps = [
            "Let x and y be arbitrary group elements.",
            "The candidate inverse of mul(x,y) is mul(inv(y),inv(x)).",
            "Multiplying mul(x,y) by this candidate inverse and reassociating reduces the middle product mul(y,inv(y)) to e.",
            "The remaining product mul(x,inv(x)) also reduces to e.",
            "The reverse multiplication is analogous, using mul(inv(x),x) and mul(inv(y),y).",
            "Therefore mul(inv(y),inv(x)) is the two-sided inverse of mul(x,y).",
        ]
        premise_loop = problem.metadata.get("premise_loop", {})
        if premise_loop.get("promoted_generated_lemma_ids"):
            steps.append(
                "Mathformer proves the candidate-inverse and uniqueness helper lemmas separately from the selected group axioms, then promotes only those proved lemmas into the minimized ATP problem."
            )
        steps.append(
            "By the group inverse axioms, Vampire proves inv(mul(x,y)) = mul(inv(y),inv(x)) by refuting the negated equality."
        )
        return steps
    if (
        problem
        and problem.metadata.get("autoformalization_strategy")
        == "group triple inverse product theorem"
    ):
        steps = [
            "Let x, y, and z be arbitrary group elements.",
            "View mul(mul(x,y),z) as the product of mul(x,y) and z.",
            "The binary inverse-of-product lemma gives inv(mul(mul(x,y),z)) = mul(inv(z),inv(mul(x,y))).",
            "Apply the same binary lemma again to rewrite inv(mul(x,y)) as mul(inv(y),inv(x)).",
            "Substituting that equality gives inv(mul(mul(x,y),z)) = mul(inv(z),mul(inv(y),inv(x))).",
        ]
        premise_loop = problem.metadata.get("premise_loop", {})
        if premise_loop.get("promoted_generated_lemma_ids"):
            steps.append(
                "Mathformer first proves the binary inverse-of-product helper from the selected group axioms, promotes only that proved lemma, and uses it in the minimized ATP problem."
            )
        steps.append(
            "Vampire verifies the universal equality by refuting its negation."
        )
        return steps
    if problem:
        return _generic_formula_steps(problem)
    return [
        "Vampire returned an SZS proof status for the supplied TPTP problem.",
        "The emitted TSTP proof is the authoritative formal proof object.",
        "The informal reading is that the conjecture follows because the negated problem is refutable.",
    ]


def _render_informal_proof(
    *,
    problem_id: str,
    status: str | None,
    statement: str,
    source_url: str | None,
    formal_step_count: int,
    steps: list[str],
) -> str:
    """Document the responsibility of ``_render_informal_proof``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        f"# Informal Proof: {problem_id}",
        "",
        f"Status: `{status or 'unknown'}`",
        f"Formal TSTP steps: {formal_step_count}",
    ]
    if source_url:
        lines.append(f"Source: {source_url}")
    if statement:
        lines.extend(["", "## Statement", "", statement.strip()])
    lines.extend(["", "## Informalized Proof", ""])
    lines.extend(f"{index}. {step}" for index, step in enumerate(steps, start=1))
    lines.extend(
        [
            "",
            "## Formal Link",
            "",
            "This explanation is derived from the generated TPTP problem and Vampire's SZS/TSTP result. "
            "The formal proof artifact remains the authoritative proof object.",
        ]
    )
    return "\n".join(lines) + "\n"


def informalize_proof(
    result: ATPResult,
    *,
    problem: ATPProblem | None = None,
    problem_path: Path | None = None,
) -> InformalProof:
    """Document the responsibility of ``informalize_proof``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``informalize_proof`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    proof_text = result.formal_proof or result.proof
    problem_id = (
        problem.problem_id
        if problem
        else (problem_path.stem if problem_path else Path(result.problem_path).stem)
    )
    statement = (
        problem.informal_statement
        if problem
        else f"TPTP problem at {result.problem_path}."
    )
    source_url = problem.source_url if problem else None
    formal_step_count = count_tstp_steps(proof_text)
    if not result.proof_found:
        steps = [
            "Vampire did not return a proof status for this attempt.",
            "Inspect the formal result JSON for the SZS status, stderr, and stdout.",
        ]
    else:
        steps = _informal_steps(problem)
    text = _render_informal_proof(
        problem_id=problem_id,
        status=result.status,
        statement=statement,
        source_url=source_url,
        formal_step_count=formal_step_count,
        steps=steps,
    )
    return InformalProof(
        ok=result.proof_found,
        style="informalized_vampire_tstp",
        problem_id=problem_id,
        status=result.status,
        statement=statement,
        source_url=source_url,
        formal_step_count=formal_step_count,
        steps=steps,
        text=text,
    )


class VampireRunner:
    """Run Vampire on TPTP problems and return parsed SZS results."""

    def __init__(self, binary: str | None = None) -> None:
        """Document the responsibility of ``VampireRunner.__init__``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Initialize instance state while keeping constructor assumptions explicit for future maintainers.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        resolved = binary or os.environ.get("VAMPIRE_BIN") or shutil.which("vampire")
        self.binary: str = resolved if resolved else ""
        if not self.binary:
            raise FileNotFoundError(
                "Vampire binary not found. Install Vampire for your platform "
                "and ensure `vampire` is on PATH, or set VAMPIRE_BIN to an "
                "executable path. See docs/getting-started/INSTALL.md for platform notes."
            )

    def version(self) -> str:
        """Document the responsibility of ``VampireRunner.version``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Run the local workflow step and surface success, failure, and evidence in a predictable form.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        result = subprocess.run(
            [self.binary, "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return (result.stdout or result.stderr).strip()

    def command(
        self, problem_path: Path, *, time_limit: int = 10, proof: bool = True
    ) -> list[str]:
        """Document the responsibility of ``VampireRunner.command``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Run the local workflow step and surface success, failure, and evidence in a predictable form.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        command = [
            self.binary,
            "--input_syntax",
            "tptp",
            "--mode",
            "portfolio",
            "--time_limit",
            str(time_limit),
        ]
        if proof:
            command.extend(["--proof", "tptp"])
        command.append(str(problem_path))
        return command

    def run_path(
        self, problem_path: Path, *, time_limit: int = 10, proof: bool = True
    ) -> ATPResult:
        """Document the responsibility of ``VampireRunner.run_path``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Run the local workflow step and surface success, failure, and evidence in a predictable form.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        problem_path = problem_path.resolve()
        command = self.command(problem_path, time_limit=time_limit, proof=proof)
        start = time.monotonic()
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        elapsed = time.monotonic() - start
        combined = completed.stdout + "\n" + completed.stderr
        status = parse_szs_status(combined)
        proof_text = parse_tstp_proof(combined)
        proof_found = status in PROOF_STATUSES
        ok = completed.returncode == 0 and proof_found
        result = ATPResult(
            ok=ok,
            proof_found=proof_found,
            status=status,
            problem_path=str(problem_path),
            command=command,
            returncode=completed.returncode,
            elapsed_seconds=elapsed,
            stdout=completed.stdout,
            stderr=completed.stderr,
            proof=proof_text,
            formal_proof=proof_text,
        )
        result.informal_proof = informalize_proof(result, problem_path=problem_path)
        return result

    def run_problem(
        self,
        problem: ATPProblem,
        *,
        output_path: Path | None = None,
        time_limit: int = 10,
        proof: bool = True,
    ) -> ATPResult:
        """Document the responsibility of ``VampireRunner.run_problem``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Run the local workflow step and surface success, failure, and evidence in a predictable form.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if output_path is not None:
            problem_path = problem.write(output_path)
            result = self.run_path(problem_path, time_limit=time_limit, proof=proof)
            result.informal_proof = informalize_proof(
                result, problem=problem, problem_path=problem_path
            )
            return result
        with tempfile.TemporaryDirectory(prefix="mathformer-vampire-") as temp_dir:
            problem_path = problem.write(Path(temp_dir) / f"{problem.problem_id}.p")
            result = self.run_path(problem_path, time_limit=time_limit, proof=proof)
            result.informal_proof = informalize_proof(
                result, problem=problem, problem_path=problem_path
            )
            return result


def subset_transitive_problem(
    *,
    problem_id: str = "subset_relation_is_transitive",
    source_url: str | None = None,
    informal_statement: str | None = None,
) -> ATPProblem:
    """Document the responsibility of ``subset_transitive_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``subset_transitive_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = informal_statement or (
        "If R is a subset of S and S is a subset of T, then R is a subset of T."
    )
    return ATPProblem(
        problem_id=problem_id,
        informal_statement=statement,
        source_url=source_url,
        metadata={
            "autoformalization_strategy": "subset predicate plus membership-definition expansion",
            "logic": "TPTP FOF",
        },
        formulas=[
            TPTPFormula(
                "subset_definition",
                "axiom",
                "! [A,B] : ( subset(A,B) <=> (! [X] : ( member(X,A) => member(X,B) )) )",
            ),
            TPTPFormula("given_r_subset_s", "axiom", "subset(r,s)"),
            TPTPFormula("given_s_subset_t", "axiom", "subset(s,t)"),
            TPTPFormula("goal_r_subset_t", "conjecture", "subset(r,t)"),
        ],
    )


def membership_chain_problem(
    *,
    problem_id: str = "subset_relation_membership_chain",
    source_url: str | None = None,
    informal_statement: str | None = None,
) -> ATPProblem:
    """Document the responsibility of ``membership_chain_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``membership_chain_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = informal_statement or (
        "If every element of R is in S and every element of S is in T, then every element of R is in T."
    )
    return ATPProblem(
        problem_id=problem_id,
        informal_statement=statement,
        source_url=source_url,
        metadata={
            "autoformalization_strategy": "direct elementwise implication chain",
            "logic": "TPTP FOF",
        },
        formulas=[
            TPTPFormula("r_to_s", "axiom", "! [X] : ( member(X,r) => member(X,s) )"),
            TPTPFormula("s_to_t", "axiom", "! [X] : ( member(X,s) => member(X,t) )"),
            TPTPFormula(
                "r_to_t", "conjecture", "! [X] : ( member(X,r) => member(X,t) )"
            ),
        ],
    )


def unary_implication_chain_problem(
    start_label: str,
    middle_label: str,
    end_label: str,
    *,
    problem_id: str | None = None,
    source_url: str | None = None,
    informal_statement: str | None = None,
) -> ATPProblem:
    """Document the responsibility of ``unary_implication_chain_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``unary_implication_chain_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    start_predicate = _predicate_name(start_label)
    middle_predicate = _predicate_name(middle_label)
    end_predicate = _predicate_name(end_label)
    statement = informal_statement or (
        f"Every {start_label} is a {middle_label}. "
        f"Every {middle_label} is a {end_label}. "
        f"Therefore every {start_label} is a {end_label}."
    )
    return ATPProblem(
        problem_id=problem_id
        or f"unary_implication_chain_{start_predicate}_to_{end_predicate}",
        informal_statement=statement,
        source_url=source_url,
        metadata={
            "autoformalization_strategy": "unary predicate implication chain",
            "logic": "TPTP FOF",
            "start_label": start_label,
            "middle_label": middle_label,
            "end_label": end_label,
            "start_predicate": start_predicate,
            "middle_predicate": middle_predicate,
            "end_predicate": end_predicate,
        },
        formulas=[
            TPTPFormula(
                f"{start_predicate}_to_{middle_predicate}",
                "axiom",
                f"! [X] : ( {start_predicate}(X) => {middle_predicate}(X) )",
            ),
            TPTPFormula(
                f"{middle_predicate}_to_{end_predicate}",
                "axiom",
                f"! [X] : ( {middle_predicate}(X) => {end_predicate}(X) )",
            ),
            TPTPFormula(
                f"{start_predicate}_to_{end_predicate}",
                "conjecture",
                f"! [X] : ( {start_predicate}(X) => {end_predicate}(X) )",
            ),
        ],
    )


def transitive_irreflexive_asymmetric_problem(
    *,
    problem_id: str = "transitive_irreflexive_relation_is_asymmetric",
    source_url: str | None = None,
    informal_statement: str | None = None,
) -> ATPProblem:
    """Document the responsibility of ``transitive_irreflexive_asymmetric_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``transitive_irreflexive_asymmetric_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = informal_statement or (
        "Every transitive and irreflexive binary relation is asymmetric."
    )
    return ATPProblem(
        problem_id=problem_id,
        informal_statement=statement,
        source_url=source_url,
        metadata={
            "autoformalization_strategy": "transitive irreflexive relation asymmetry",
            "logic": "TPTP FOF",
            "relation_predicate": "r",
        },
        formulas=[
            TPTPFormula(
                "r_transitive",
                "axiom",
                "! [X,Y,Z] : ( ( r(X,Y) & r(Y,Z) ) => r(X,Z) )",
            ),
            TPTPFormula(
                "r_irreflexive",
                "axiom",
                "! [X] : ~ r(X,X)",
            ),
            TPTPFormula(
                "r_asymmetric",
                "conjecture",
                "! [X,Y] : ( r(X,Y) => ~ r(Y,X) )",
            ),
        ],
    )


def group_inverse_product_problem(
    *,
    problem_id: str = "group_inverse_of_product_reverses_order",
    source_url: str | None = None,
    informal_statement: str | None = None,
) -> ATPProblem:
    """Document the responsibility of ``group_inverse_product_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``group_inverse_product_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = informal_statement or (
        "In a group, the inverse of a product is the product of the inverses in reverse order."
    )
    return ATPProblem(
        problem_id=problem_id,
        informal_statement=statement,
        source_url=source_url,
        metadata={
            "autoformalization_strategy": "group inverse product theorem",
            "logic": "TPTP FOF with equality",
            "operation": "mul",
            "identity": "e",
            "inverse": "inv",
        },
        formulas=[
            TPTPFormula(
                "mul_associative",
                "axiom",
                "! [X,Y,Z] : ( mul(mul(X,Y),Z) = mul(X,mul(Y,Z)) )",
            ),
            TPTPFormula(
                "left_identity",
                "axiom",
                "! [X] : ( mul(e,X) = X )",
            ),
            TPTPFormula(
                "right_identity",
                "axiom",
                "! [X] : ( mul(X,e) = X )",
            ),
            TPTPFormula(
                "left_inverse",
                "axiom",
                "! [X] : ( mul(inv(X),X) = e )",
            ),
            TPTPFormula(
                "right_inverse",
                "axiom",
                "! [X] : ( mul(X,inv(X)) = e )",
            ),
            TPTPFormula(
                "inverse_product_reverse_order",
                "conjecture",
                "! [X,Y] : ( inv(mul(X,Y)) = mul(inv(Y),inv(X)) )",
            ),
        ],
    )


def group_triple_inverse_product_problem(
    *,
    problem_id: str = "group_inverse_of_triple_product_reverses_order",
    source_url: str | None = None,
    informal_statement: str | None = None,
) -> ATPProblem:
    """Document the responsibility of ``group_triple_inverse_product_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``group_triple_inverse_product_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = informal_statement or (
        "In a group, the inverse of a product of three elements is the product of the inverses in reverse order."
    )
    return ATPProblem(
        problem_id=problem_id,
        informal_statement=statement,
        source_url=source_url,
        metadata={
            "autoformalization_strategy": "group triple inverse product theorem",
            "logic": "TPTP FOF with equality",
            "operation": "mul",
            "identity": "e",
            "inverse": "inv",
        },
        formulas=[
            TPTPFormula(
                "mul_associative",
                "axiom",
                "! [X,Y,Z] : ( mul(mul(X,Y),Z) = mul(X,mul(Y,Z)) )",
            ),
            TPTPFormula(
                "left_identity",
                "axiom",
                "! [X] : ( mul(e,X) = X )",
            ),
            TPTPFormula(
                "right_identity",
                "axiom",
                "! [X] : ( mul(X,e) = X )",
            ),
            TPTPFormula(
                "left_inverse",
                "axiom",
                "! [X] : ( mul(inv(X),X) = e )",
            ),
            TPTPFormula(
                "right_inverse",
                "axiom",
                "! [X] : ( mul(X,inv(X)) = e )",
            ),
            TPTPFormula(
                "inverse_triple_product_reverse_order",
                "conjecture",
                "! [X,Y,Z] : ( inv(mul(mul(X,Y),Z)) = mul(inv(Z),mul(inv(Y),inv(X))) )",
            ),
        ],
    )


def aggressive_autoformalize(
    informal_statement: str,
    *,
    source_url: str | None = None,
) -> list[ATPProblem]:
    """Generate a small portfolio of TPTP candidates from informal mathematics."""

    normalized = informal_statement.lower()
    unary_chain = _parse_unary_implication_chain(informal_statement)
    if unary_chain:
        start_label, middle_label, end_label = unary_chain
        return [
            unary_implication_chain_problem(
                start_label,
                middle_label,
                end_label,
                source_url=source_url,
                informal_statement=informal_statement,
            )
        ]
    if (
        "transitive" in normalized
        and "irreflexive" in normalized
        and "asymmetric" in normalized
    ):
        return [
            transitive_irreflexive_asymmetric_problem(
                source_url=source_url,
                informal_statement=informal_statement,
            )
        ]
    if (
        "group" in normalized
        and "inverse" in normalized
        and "product" in normalized
        and (
            "three" in normalized
            or "triple" in normalized
            or "x, y, and z" in normalized
        )
    ):
        return [
            group_triple_inverse_product_problem(
                source_url=source_url,
                informal_statement=informal_statement,
            )
        ]
    if "group" in normalized and "inverse" in normalized and "product" in normalized:
        return [
            group_inverse_product_problem(
                source_url=source_url,
                informal_statement=informal_statement,
            )
        ]
    if "subset" in normalized and (
        "transitive" in normalized or "subset of t" in normalized
    ):
        return [
            subset_transitive_problem(
                source_url=source_url,
                informal_statement=informal_statement,
            ),
            membership_chain_problem(
                source_url=source_url,
                informal_statement=informal_statement,
            ),
        ]
    raise ValueError(
        "No built-in aggressive autoformalization template matched the statement. "
        "Add a domain template or pass an explicit TPTP problem."
    )


def _candidate_formula(
    candidate: PremiseCandidate, *, role: str = "axiom"
) -> TPTPFormula:
    """Document the responsibility of ``_candidate_formula``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_candidate_formula`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return TPTPFormula(
        name=candidate.name,
        role=role,
        formula=candidate.formula,
        language=candidate.language,
    )


def _conjecture_formulas(problem: ATPProblem) -> list[TPTPFormula]:
    """Document the responsibility of ``_conjecture_formulas``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_conjecture_formulas`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [formula for formula in problem.formulas if formula.role == "conjecture"]


def _problem_from_premises(
    problem: ATPProblem,
    premises: Sequence[PremiseCandidate],
    *,
    problem_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ATPProblem:
    """Document the responsibility of ``_problem_from_premises``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_problem_from_premises`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    merged_metadata = dict(problem.metadata)
    if metadata:
        merged_metadata.update(metadata)
    return ATPProblem(
        problem_id=problem_id or problem.problem_id,
        informal_statement=problem.informal_statement,
        source_url=problem.source_url,
        metadata=merged_metadata,
        formulas=[_candidate_formula(candidate, role="axiom") for candidate in premises]
        + _conjecture_formulas(problem),
    )


def _lemma_problem(
    problem: ATPProblem,
    premises: Sequence[PremiseCandidate],
    lemma: PremiseCandidate,
    *,
    problem_id: str,
) -> ATPProblem:
    """Document the responsibility of ``_lemma_problem``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_lemma_problem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return ATPProblem(
        problem_id=problem_id,
        informal_statement=problem.informal_statement,
        source_url=problem.source_url,
        metadata={
            **problem.metadata,
            "proof_obligation": "generated_lemma",
            "main_problem_id": problem.problem_id,
            "generated_lemma_id": lemma.id,
            "premise_ids": [candidate.id for candidate in premises],
        },
        formulas=[_candidate_formula(candidate, role="axiom") for candidate in premises]
        + [TPTPFormula(lemma.name, "conjecture", lemma.formula, lemma.language)],
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Document the responsibility of ``_write_json``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _persist_result_artifacts(
    *,
    result: ATPResult,
    result_path: Path,
    proof_path: Path,
    informal_path: Path,
    informal_json_path: Path,
) -> None:
    """Document the responsibility of ``_persist_result_artifacts``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_persist_result_artifacts`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result.write_json(result_path)
    if result.formal_proof:
        proof_path.write_text(result.formal_proof + "\n", encoding="utf-8")
    if result.informal_proof:
        informal_path.write_text(result.informal_proof.text, encoding="utf-8")
        _write_json(informal_json_path, result.informal_proof.to_dict())


def _drain_steps(steps):
    """Synchronous callers share the exact same algorithm as staged callers."""
    while True:
        try:
            next(steps)
        except StopIteration as completed:
            return completed.value


def _prove_generated_lemmas(
    *,
    problem: ATPProblem,
    selected: Sequence[PremiseCandidate],
    artifact_root: Path,
    runner: VampireRunner,
    time_limit: int,
) -> tuple[list[PremiseCandidate], dict[str, Any], str]:
    """Drain the shared staged native implementation."""
    return _drain_steps(
        _prove_generated_lemmas_steps(
            problem=problem,
            selected=selected,
            artifact_root=artifact_root,
            runner=runner,
            time_limit=time_limit,
        )
    )


def _prove_generated_lemmas_steps(
    *,
    problem: ATPProblem,
    selected: Sequence[PremiseCandidate],
    artifact_root: Path,
    runner: VampireRunner,
    time_limit: int,
    workflow_stages: bool = False,
) -> Generator[
    tuple[str, dict[str, Any]], None, tuple[list[PremiseCandidate], dict[str, Any], str]
]:
    """Document the responsibility of ``_prove_generated_lemmas``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_prove_generated_lemmas`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    generated_lemmas = generate_candidate_lemmas(problem, list(selected))
    lemma_root = artifact_root / "premise_generation"
    lemma_root.mkdir(parents=True, exist_ok=True)
    promoted: list[PremiseCandidate] = []

    yield (
        "select_pack",
        {
            "selected_ids": [p.id for p in selected],
            "generated_count": len(generated_lemmas),
        },
    )
    if not generated_lemmas:
        yield "lemma_step", {"done": True}
    for index, generated in enumerate(generated_lemmas, start=1):
        if not generated.attempt_proof:
            yield (
                "lemma_step",
                {"done": index == len(generated_lemmas), "skipped": generated.id},
            )
            continue
        lemma_problem_id = f"{problem.problem_id}__lemma__{generated.id}"
        safe_id = re.sub(r"[^A-Za-z0-9_]+", "_", generated.id).strip("_")
        problem_path = lemma_root / f"{index:02d}_{safe_id}.p"
        result_path = lemma_root / f"{index:02d}_{safe_id}.result.json"
        proof_path = lemma_root / f"{index:02d}_{safe_id}.proof.tstp"
        lemma_problem = _lemma_problem(
            problem,
            selected,
            generated.candidate,
            problem_id=lemma_problem_id,
        )
        result = runner.run_problem(
            lemma_problem, output_path=problem_path, time_limit=time_limit
        )
        result.write_json(result_path)
        if result.formal_proof:
            proof_path.write_text(result.formal_proof + "\n", encoding="utf-8")
        generated.problem_path = str(problem_path)
        generated.result_path = str(result_path)
        generated.elapsed_seconds = result.elapsed_seconds
        if result.proof_found:
            generated.proof_status = result.status or "proved"
            generated.promoted = True
            generated.proof_path = str(proof_path)
            generated.candidate.premise_type = "proved_generated_lemma"
            generated.candidate.formula_role = "axiom"
            generated.candidate.provenance = (
                f"proved generated lemma from {lemma_problem_id}; proof at {proof_path}"
            )
            generated.candidate.rejected_reason = None
            promoted.append(generated.candidate)
        else:
            generated.proof_status = result.status or "not_proved"
            generated.promoted = False
            generated.rejection_reason = "Vampire did not prove this generated lemma."
            generated.candidate.premise_type = "rejected_generated_lemma"
            generated.candidate.rejected_reason = generated.rejection_reason

        yield (
            "lemma_step",
            {
                "done": index == len(generated_lemmas),
                "promoted_ids": [p.id for p in promoted],
            },
        )

    report = build_generation_report(problem.problem_id, generated_lemmas)
    report_path = artifact_root / "premise_generation_report.json"
    _write_json(report_path, report.to_dict())
    if workflow_stages:
        yield "generation_finish", report.to_dict()
    return promoted, report.to_dict(), str(report_path)


def _minimize_premises(
    *,
    problem: ATPProblem,
    premises: Sequence[PremiseCandidate],
    artifact_root: Path,
    runner: VampireRunner,
    time_limit: int,
    enabled: bool,
) -> tuple[list[PremiseCandidate], list[dict[str, Any]], str | None]:
    """Drain the shared staged native implementation."""
    return _drain_steps(
        _minimize_premises_steps(
            problem=problem,
            premises=premises,
            artifact_root=artifact_root,
            runner=runner,
            time_limit=time_limit,
            enabled=enabled,
        )
    )


def _minimize_premises_steps(
    *,
    problem: ATPProblem,
    premises: Sequence[PremiseCandidate],
    artifact_root: Path,
    runner: VampireRunner,
    time_limit: int,
    enabled: bool,
    workflow_stages: bool = False,
) -> Generator[
    tuple[str, dict[str, Any]],
    None,
    tuple[list[PremiseCandidate], list[dict[str, Any]], str | None],
]:
    """Document the responsibility of ``_minimize_premises``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_minimize_premises`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not enabled:
        return list(premises), [], None

    current = list(premises)
    attempts: list[dict[str, Any]] = []
    min_root = artifact_root / "premise_minimization"
    min_root.mkdir(parents=True, exist_ok=True)

    yield "augment_pack", {"initial_ids": [p.id for p in premises]}
    if not premises:
        yield "deletion_step", {"done": True}
    for index, candidate in enumerate(list(premises), start=1):
        if candidate not in current:
            yield "deletion_step", {"done": index == len(premises)}
            continue
        trial = [item for item in current if item.id != candidate.id]
        trial_problem = _problem_from_premises(
            problem,
            trial,
            problem_id=f"{problem.problem_id}__minimize_without__{candidate.id}",
            metadata={
                "proof_obligation": "premise_minimization",
                "removed_premise_id": candidate.id,
                "trial_premise_ids": [item.id for item in trial],
            },
        )
        safe_id = re.sub(r"[^A-Za-z0-9_]+", "_", candidate.id).strip("_")
        problem_path = min_root / f"{index:02d}_without_{safe_id}.p"
        result_path = min_root / f"{index:02d}_without_{safe_id}.result.json"
        minimization_time_limit = max(1, min(time_limit, 1))
        result = runner.run_problem(
            trial_problem,
            output_path=problem_path,
            time_limit=minimization_time_limit,
            proof=False,
        )
        result.write_json(result_path)
        if result.proof_found:
            current = trial
        attempts.append(
            {
                "removed_premise_id": candidate.id,
                "ok_without_premise": result.proof_found,
                "kept": not result.proof_found,
                "status": result.status,
                "problem_path": str(problem_path),
                "result_path": str(result_path),
            }
        )

        yield (
            "deletion_step",
            {
                "done": index == len(premises),
                "current_ids": [p.id for p in current],
                "attempts": list(attempts),
            },
        )

    report = {
        "problem_id": problem.problem_id,
        "initial_premise_ids": [candidate.id for candidate in premises],
        "final_premise_ids": [candidate.id for candidate in current],
        "attempts": attempts,
        "notes": [
            "A premise is removed only when Vampire still proves the theorem without it.",
            "Generated lemmas are eligible for the final set only after separate proof promotion.",
        ],
    }
    report_path = artifact_root / "premise_minimization_report.json"
    _write_json(report_path, report)
    if workflow_stages:
        yield "minimization_finish", report
    return current, attempts, str(report_path)


def _run_premise_guided_attempt(
    *,
    problem: ATPProblem,
    artifact_root: Path,
    candidate_index: int,
    runner: VampireRunner,
    time_limit: int,
    premise_budget: str,
    generate_premises: bool,
    minimize_premises: bool,
) -> dict[str, Any]:
    """Drain the shared staged native implementation."""
    return _drain_steps(
        _run_premise_guided_attempt_steps(
            problem=problem,
            artifact_root=artifact_root,
            candidate_index=candidate_index,
            runner=runner,
            time_limit=time_limit,
            premise_budget=premise_budget,
            generate_premises=generate_premises,
            minimize_premises=minimize_premises,
        )
    )


def _run_premise_guided_attempt_steps(
    *,
    problem: ATPProblem,
    artifact_root: Path,
    candidate_index: int,
    runner: VampireRunner,
    time_limit: int,
    premise_budget: str,
    generate_premises: bool,
    minimize_premises: bool,
    workflow_stages: bool = False,
) -> Generator[tuple[str, dict[str, Any]], None, dict[str, Any]]:
    """Document the responsibility of ``_run_premise_guided_attempt``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    registry = build_premise_registry(problem)
    selection_report = select_premises(problem, registry, budget=premise_budget)
    selected = selected_candidates(selection_report)
    selection_report_path = artifact_root / "premise_selection_report.json"
    _write_json(selection_report_path, selection_report.to_dict())

    if workflow_stages:
        yield "selection", selection_report.to_dict()

    promoted: list[PremiseCandidate] = []
    generation_report: dict[str, Any] | None = None
    generation_report_path: str | None = None
    if generate_premises:
        (
            promoted,
            generation_report,
            generation_report_path,
        ) = yield from _prove_generated_lemmas_steps(
            problem=problem,
            selected=selected,
            artifact_root=artifact_root,
            runner=runner,
            time_limit=time_limit,
            workflow_stages=workflow_stages,
        )
    else:
        generation_report = {
            "problem_id": problem.problem_id,
            "generated_count": 0,
            "attempted_count": 0,
            "proved_count": 0,
            "promoted_ids": [],
            "generated_lemmas": [],
            "notes": ["Premise generation disabled for this attempt."],
        }

    if workflow_stages and not generate_premises:
        yield "generation_bypass", generation_report

    augmented = selected + promoted
    (
        minimized,
        minimization_attempts,
        minimization_report_path,
    ) = yield from _minimize_premises_steps(
        problem=problem,
        premises=augmented,
        artifact_root=artifact_root,
        runner=runner,
        time_limit=time_limit,
        enabled=minimize_premises,
        workflow_stages=workflow_stages,
    )
    if workflow_stages and not minimize_premises:
        yield "minimization_bypass", {"final_ids": [p.id for p in minimized]}
    final_metadata = {
        "premise_loop": {
            "enabled": True,
            "budget": premise_budget,
            "selected_premise_ids": [candidate.id for candidate in selected],
            "promoted_generated_lemma_ids": [candidate.id for candidate in promoted],
            "final_premise_ids": [candidate.id for candidate in minimized],
            "generation_enabled": generate_premises,
            "minimization_enabled": minimize_premises,
        }
    }
    final_problem = _problem_from_premises(problem, minimized, metadata=final_metadata)

    problem_path = (
        artifact_root / f"candidate_{candidate_index:02d}_{problem.problem_id}.p"
    )
    result_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.result.json"
    )
    proof_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.proof.tstp"
    )
    informal_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.informal.md"
    )
    informal_json_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.informal.json"
    )
    result = runner.run_problem(
        final_problem, output_path=problem_path, time_limit=time_limit
    )
    _persist_result_artifacts(
        result=result,
        result_path=result_path,
        proof_path=proof_path,
        informal_path=informal_path,
        informal_json_path=informal_json_path,
    )

    return {
        "problem": final_problem,
        "result": result,
        "problem_path": problem_path,
        "result_path": result_path,
        "proof_path": proof_path if result.formal_proof else None,
        "formal_proof_path": proof_path if result.formal_proof else None,
        "informal_proof_path": informal_path if result.informal_proof else None,
        "informal_proof_json_path": (
            informal_json_path if result.informal_proof else None
        ),
        "premise_selection_report": selection_report.to_dict(),
        "premise_selection_report_path": str(selection_report_path),
        "premise_generation_report": generation_report,
        "premise_generation_report_path": generation_report_path,
        "premise_minimization_attempts": minimization_attempts,
        "premise_minimization_report_path": minimization_report_path,
        "final_premise_ids": [candidate.id for candidate in minimized],
    }


def _run_direct_attempt(
    *,
    problem: ATPProblem,
    artifact_root: Path,
    candidate_index: int,
    runner: VampireRunner,
    time_limit: int,
) -> dict[str, Any]:
    """Document the responsibility of ``_run_direct_attempt``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    problem_path = (
        artifact_root / f"candidate_{candidate_index:02d}_{problem.problem_id}.p"
    )
    result_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.result.json"
    )
    proof_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.proof.tstp"
    )
    informal_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.informal.md"
    )
    informal_json_path = (
        artifact_root
        / f"candidate_{candidate_index:02d}_{problem.problem_id}.informal.json"
    )
    result = runner.run_problem(
        problem, output_path=problem_path, time_limit=time_limit
    )
    _persist_result_artifacts(
        result=result,
        result_path=result_path,
        proof_path=proof_path,
        informal_path=informal_path,
        informal_json_path=informal_json_path,
    )
    return {
        "problem": problem,
        "result": result,
        "problem_path": problem_path,
        "result_path": result_path,
        "proof_path": proof_path if result.formal_proof else None,
        "formal_proof_path": proof_path if result.formal_proof else None,
        "informal_proof_path": informal_path if result.informal_proof else None,
        "informal_proof_json_path": (
            informal_json_path if result.informal_proof else None
        ),
        "final_premise_ids": [
            formula.name for formula in problem.formulas if formula.role != "conjecture"
        ],
    }


def discover_proof(
    informal_statement: str,
    *,
    artifact_root: Path,
    source_url: str | None = None,
    time_limit: int = 10,
    runner: VampireRunner | None = None,
    premise_loop: bool = False,
    premise_budget: str = "medium",
    generate_premises: bool = True,
    minimize_premises: bool = True,
) -> dict[str, Any]:
    """Drain the shared staged native implementation."""
    return _drain_steps(
        discover_proof_steps(
            informal_statement=informal_statement,
            artifact_root=artifact_root,
            source_url=source_url,
            time_limit=time_limit,
            runner=runner,
            premise_loop=premise_loop,
            premise_budget=premise_budget,
            generate_premises=generate_premises,
            minimize_premises=minimize_premises,
        )
    )


def discover_proof_steps(
    informal_statement: str,
    *,
    artifact_root: Path,
    source_url: str | None = None,
    time_limit: int = 10,
    runner: VampireRunner | None = None,
    premise_loop: bool = False,
    premise_budget: str = "medium",
    generate_premises: bool = True,
    minimize_premises: bool = True,
    workflow_stages: bool = False,
) -> Generator[tuple[str, dict[str, Any]], None, dict[str, Any]]:
    """Autoformalize an informal statement, run Vampire, and persist the first proof found."""

    runner = runner or VampireRunner()
    artifact_root.mkdir(parents=True, exist_ok=True)
    candidates = aggressive_autoformalize(informal_statement, source_url=source_url)
    attempts: list[dict[str, Any]] = []
    winning_result: ATPResult | None = None
    winning_problem: ATPProblem | None = None
    winning_attempt: dict[str, Any] | None = None
    yield "initialize", {"candidate_count": len(candidates)}
    for index, problem in enumerate(candidates, start=1):
        if premise_loop:
            raw_attempt = yield from _run_premise_guided_attempt_steps(
                problem=problem,
                artifact_root=artifact_root,
                candidate_index=index,
                runner=runner,
                time_limit=time_limit,
                premise_budget=premise_budget,
                generate_premises=generate_premises,
                minimize_premises=minimize_premises,
                workflow_stages=workflow_stages,
            )
        else:
            raw_attempt = _run_direct_attempt(
                problem=problem,
                artifact_root=artifact_root,
                candidate_index=index,
                runner=runner,
                time_limit=time_limit,
            )
        yield (
            "final_attempt",
            {
                "final_premise_ids": raw_attempt.get("final_premise_ids", []),
                "proof_found": raw_attempt["result"].proof_found,
            },
        )
        result = raw_attempt["result"]
        final_problem = raw_attempt["problem"]
        attempt = {
            "problem": final_problem.to_dict(),
            "original_problem": problem.to_dict(),
            "problem_path": str(raw_attempt["problem_path"]),
            "result_path": str(raw_attempt["result_path"]),
            "proof_path": (
                str(raw_attempt["proof_path"]) if raw_attempt["proof_path"] else None
            ),
            "formal_proof_path": (
                str(raw_attempt["formal_proof_path"])
                if raw_attempt["formal_proof_path"]
                else None
            ),
            "informal_proof_path": (
                str(raw_attempt["informal_proof_path"])
                if raw_attempt["informal_proof_path"]
                else None
            ),
            "informal_proof_json_path": (
                str(raw_attempt["informal_proof_json_path"])
                if raw_attempt["informal_proof_json_path"]
                else None
            ),
            "premise_selection_report_path": raw_attempt.get(
                "premise_selection_report_path"
            ),
            "premise_generation_report_path": raw_attempt.get(
                "premise_generation_report_path"
            ),
            "premise_minimization_report_path": raw_attempt.get(
                "premise_minimization_report_path"
            ),
            "premise_selection_report": raw_attempt.get("premise_selection_report"),
            "premise_generation_report": raw_attempt.get("premise_generation_report"),
            "premise_minimization_attempts": raw_attempt.get(
                "premise_minimization_attempts", []
            ),
            "final_premise_ids": raw_attempt.get("final_premise_ids", []),
            "result": result.to_dict(),
        }
        attempts.append(attempt)
        if result.proof_found and winning_result is None:
            winning_result = result
            winning_problem = final_problem
            winning_attempt = attempt
        yield (
            "carry_candidate",
            {
                "done": result.proof_found or index == len(candidates),
                "attempt_count": len(attempts),
                "winner": winning_problem.problem_id if winning_problem else None,
            },
        )
        if winning_result is not None:
            break
    report = {
        "backend": "vampire",
        "style": "tptp_fof_atp_search",
        "generated_at": now(),
        "ok": winning_result is not None and winning_result.proof_found,
        "source_url": source_url,
        "informal_statement": informal_statement,
        "premise_loop": {
            "enabled": premise_loop,
            "budget": premise_budget,
            "generation_enabled": generate_premises,
            "minimization_enabled": minimize_premises,
        },
        "candidate_count": len(candidates),
        "attempt_count": len(attempts),
        "winner": winning_problem.to_dict() if winning_problem else None,
        "winning_status": winning_result.status if winning_result else None,
        "winning_formal_proof": winning_result.formal_proof if winning_result else None,
        "winning_informal_proof": (
            winning_result.informal_proof.to_dict()
            if winning_result and winning_result.informal_proof
            else None
        ),
        "winning_formal_proof_path": (
            winning_attempt.get("formal_proof_path") if winning_attempt else None
        ),
        "winning_informal_proof_path": (
            winning_attempt.get("informal_proof_path") if winning_attempt else None
        ),
        "winning_premise_selection_report_path": (
            winning_attempt.get("premise_selection_report_path")
            if winning_attempt
            else None
        ),
        "winning_premise_generation_report_path": (
            winning_attempt.get("premise_generation_report_path")
            if winning_attempt
            else None
        ),
        "winning_premise_minimization_report_path": (
            winning_attempt.get("premise_minimization_report_path")
            if winning_attempt
            else None
        ),
        "winning_final_premise_ids": (
            winning_attempt.get("final_premise_ids") if winning_attempt else []
        ),
        "attempts": attempts,
        "vampire_version": runner.version(),
    }
    (artifact_root / "discovery_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def read_text_argument(text: str | None, text_file: Path | None) -> str:
    """Document the responsibility of ``read_text_argument``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if text is not None:
        return text
    if text_file is not None:
        return text_file.read_text(encoding="utf-8")
    raise ValueError("Provide --text or --text-file for autoformalization.")
