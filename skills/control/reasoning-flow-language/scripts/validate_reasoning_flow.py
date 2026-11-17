#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make epistemic flow projections machine-checkable without requiring a YAML
#   parser or coupling them to operational workflow execution.
#
# Intent:
#   Parse the compact ERFL 0.3 profile and reject category errors that could
#   silently promote dependency, execution, or calibration into warrant.
#
# Function:
#   Validates syntax, type and relation names, handle conservation, branch
#   interfaces, terminal calibration, bounded iteration, projection gaps, and
#   cross-registry consistency.
#
# Maintenance Notes:
#   Keep the parser grammar and semantic checks aligned with
#   references/erfl-0.3.json and docs/architecture/REASONING_FLOW_LANGUAGE.md.

"""Validate Mathformer Epistemic Reasoning Flow Language 0.3 files."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REGISTRY = SKILL_DIR / "references" / "erfl-0.3.json"
REASONING_REGISTRY = REPO_ROOT / "skills" / "REASONING_TYPES.yaml"
OUTPUT_REGISTRY = REPO_ROOT / "skills" / "OUTPUT_TYPES.yaml"

ID_PATTERN = r"[A-Za-z_][A-Za-z0-9_.-]*"
PORT_PATTERN = re.compile(
    rf"^(?P<name>{ID_PATTERN})(?:::(?P<kind>[A-Za-z][A-Za-z0-9_]*(?:<.*>)?))?$"
)
OCCURRENCE_PATTERN = re.compile(
    rf"(?:(?P<alias>{ID_PATTERN}):)?(?P<type>[A-Z]|_)\[(?P<ports>[^\[\]]*?->[^\[\]]*?)\](?P<optional>\?)?"
)
RELATION_PATTERN = re.compile(r"-[a-z][a-z0-9_]*>")
RESOURCE_DECLARATION_PATTERN = re.compile(
    rf"@(?P<resource_class>KB|SEARCH|STORE)\s+"
    rf"(?P<alias>{ID_PATTERN})\s+"
    rf'connect\((?P<connector>file)\("(?P<target>[^"\r\n]+)"\)\)'
)
RESOURCE_ACCESS_PATTERN = re.compile(
    rf"(?P<occurrence>{ID_PATTERN})\s+<-(?P<mode>read|lookup|query|search|snapshot)-\s+"
    rf"(?P<resource>{ID_PATTERN})"
)
RESOURCE_PERSIST_PATTERN = re.compile(
    rf"(?P<occurrence>{ID_PATTERN})\s+-(?P<mode>persist|append|put|upsert|checkpoint|invalidate|promote|commit)->\s+"
    rf"(?P<resource>{ID_PATTERN})"
)


class FlowSyntaxError(ValueError):
    """Represent a source-positioned ERFL syntax error."""


@dataclass(frozen=True)
class Port:
    name: str
    kind: Optional[str]

    @property
    def root_kind(self) -> Optional[str]:
        if self.kind is None:
            return None
        return self.kind.split("<", 1)[0]


@dataclass
class Occurrence:
    alias: str
    type_code: str
    inputs: List[Port]
    outputs: List[Port]
    optional: bool = False


@dataclass
class Parallel:
    children: List["Node"]


@dataclass
class Choice:
    children: List["Node"]


@dataclass
class SequenceNode:
    children: List["Node"]
    relations: List[str]


Node = Occurrence | Parallel | Choice | SequenceNode


@dataclass
class Handler:
    subject: str
    status: str
    action: str
    target: Optional[str]
    line: int


@dataclass
class RepeatBlock:
    minimum: int
    maximum: int
    expression: Node
    predicate_subject: str
    predicate_status: str
    measure: str
    line: int


@dataclass(frozen=True)
class ResourceBinding:
    resource_class: str
    alias: str
    connector: str
    target: str
    line: int


@dataclass(frozen=True)
class ResourceEdge:
    occurrence_alias: str
    mode: str
    resource_alias: str
    direction: str
    line: int


@dataclass
class Flow:
    name: str
    goal_text: str
    goal_handle: str
    route: Node
    repeats: List[RepeatBlock]
    handlers: List[Handler]
    resources: List[ResourceBinding]
    resource_edges: List[ResourceEdge]


@dataclass(frozen=True)
class SourceStatement:
    """One logical ERFL statement spanning one or more physical source lines."""

    start_line: int
    end_line: int
    text: str


class ExpressionParser:
    """Parse one ERFL route expression using the documented precedence."""

    def __init__(self, text: str, *, line: int | str) -> None:
        self.text = text
        self.line = line
        self.tokens = self._tokenize(text)
        self.index = 0
        self.generated_alias_index = 0

    def _tokenize(self, text: str) -> List[Tuple[str, str]]:
        tokens: List[Tuple[str, str]] = []
        cursor = 0
        while cursor < len(text):
            if text[cursor].isspace():
                cursor += 1
                continue
            if text[cursor] in "()|&":
                tokens.append((text[cursor], text[cursor]))
                cursor += 1
                continue
            relation = RELATION_PATTERN.match(text, cursor)
            if relation:
                tokens.append(("REL", relation.group()[1:-1]))
                cursor = relation.end()
                continue
            if text[cursor] == ">":
                tokens.append(("LEGACY", ">"))
                cursor += 1
                continue
            occurrence = OCCURRENCE_PATTERN.match(text, cursor)
            if occurrence:
                tokens.append(("OCC", occurrence.group()))
                cursor = occurrence.end()
                continue
            excerpt = text[cursor : cursor + 32]
            raise FlowSyntaxError(
                f"line {self.line}: cannot tokenize expression near {excerpt!r}"
            )
        return tokens

    def peek(self, token_type: Optional[str] = None) -> bool:
        if self.index >= len(self.tokens):
            return False
        return token_type is None or self.tokens[self.index][0] == token_type

    def take(self, token_type: str) -> str:
        if not self.peek(token_type):
            actual = (
                self.tokens[self.index][0] if self.index < len(self.tokens) else "EOF"
            )
            raise FlowSyntaxError(
                f"line {self.line}: expected {token_type}, found {actual}"
            )
        value = self.tokens[self.index][1]
        self.index += 1
        return value

    def parse(self) -> Node:
        if not self.tokens:
            raise FlowSyntaxError(f"line {self.line}: empty route expression")
        result = self.parse_sequence()
        if self.index != len(self.tokens):
            token_type, value = self.tokens[self.index]
            if token_type == "LEGACY":
                raise FlowSyntaxError(
                    f"line {self.line}: legacy unlabelled dependency '>' is forbidden"
                )
            raise FlowSyntaxError(
                f"line {self.line}: unexpected token {value!r} after expression"
            )
        return result

    def parse_sequence(self) -> Node:
        children = [self.parse_choice()]
        relations: List[str] = []
        while self.peek("REL") or self.peek("LEGACY"):
            if self.peek("LEGACY"):
                self.take("LEGACY")
                raise FlowSyntaxError(
                    f"line {self.line}: legacy unlabelled dependency '>' is forbidden"
                )
            relations.append(self.take("REL"))
            children.append(self.parse_choice())
        if len(children) == 1:
            return children[0]
        return SequenceNode(children=children, relations=relations)

    def parse_choice(self) -> Node:
        children = [self.parse_parallel()]
        while self.peek("|"):
            self.take("|")
            children.append(self.parse_parallel())
        if len(children) == 1:
            return children[0]
        return Choice(children=children)

    def parse_parallel(self) -> Node:
        children = [self.parse_atom()]
        while self.peek("&"):
            self.take("&")
            children.append(self.parse_atom())
        if len(children) == 1:
            return children[0]
        return Parallel(children=children)

    def parse_atom(self) -> Node:
        if self.peek("("):
            self.take("(")
            result = self.parse_sequence()
            self.take(")")
            return result
        raw = self.take("OCC")
        match = OCCURRENCE_PATTERN.fullmatch(raw)
        if not match:
            raise FlowSyntaxError(f"line {self.line}: invalid occurrence {raw!r}")
        alias = match.group("alias")
        if alias is None:
            self.generated_alias_index += 1
            alias = f"_anonymous_{self.line}_{self.generated_alias_index}"
        port_text = match.group("ports")
        input_text, output_text = port_text.split("->", 1)
        return Occurrence(
            alias=alias,
            type_code=match.group("type"),
            inputs=parse_ports(input_text, line=self.line),
            outputs=parse_ports(output_text, line=self.line),
            optional=bool(match.group("optional")),
        )


def split_top_level_commas(text: str, *, line: int | str) -> List[str]:
    """Split a port list without splitting generic parameters."""
    if not text.strip():
        return []
    result: List[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(text):
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth < 0:
                raise FlowSyntaxError(f"line {line}: unmatched '>' in port type")
        elif char == "," and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise FlowSyntaxError(f"line {line}: unmatched '<' in port type")
    result.append(text[start:].strip())
    return result


def parse_ports(text: str, *, line: int | str) -> List[Port]:
    ports: List[Port] = []
    for raw_port in split_top_level_commas(text, line=line):
        if not raw_port:
            raise FlowSyntaxError(f"line {line}: empty port in interface")
        match = PORT_PATTERN.fullmatch(raw_port)
        if not match:
            raise FlowSyntaxError(f"line {line}: invalid port {raw_port!r}")
        ports.append(Port(name=match.group("name"), kind=match.group("kind")))
    return ports


def strip_comment(raw_line: str) -> str:
    """Remove a comment marker outside a quoted goal string."""
    quoted = False
    escaped = False
    for index, char in enumerate(raw_line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
        elif char == "#" and not quoted:
            return raw_line[:index]
    return raw_line


def scan_document_statements(text: str) -> List[SourceStatement]:
    """Coalesce physical lines while keeping indentation semantically inert.

    A new logical statement starts only at a reserved flow-body keyword. This
    permits routes, repeat bodies, goals, and handlers to wrap between tokens
    without turning indentation into control flow.
    """
    lines = [
        (number, strip_comment(raw).strip())
        for number, raw in enumerate(text.splitlines(), 1)
        if strip_comment(raw).strip()
    ]
    if len(lines) < 5:
        raise FlowSyntaxError("document is incomplete")
    if lines[0][1] != "erfl 0.3":
        raise FlowSyntaxError(
            f"line {lines[0][0]}: expected exact language declaration 'erfl 0.3'"
        )
    reasoning_index = next(
        (
            index
            for index, (_, line) in enumerate(lines[1:], 1)
            if re.fullmatch(rf"reasoning\s+({ID_PATTERN})\s*\{{", line)
        ),
        None,
    )
    if reasoning_index is None:
        legacy = next(
            (line_no for line_no, line in lines if re.match(r"^flow(?:\s|$)", line)),
            None,
        )
        if legacy is not None:
            raise FlowSyntaxError(
                f"line {legacy}: legacy 'flow' declaration is forbidden; use 'reasoning'"
            )
        raise FlowSyntaxError("document has no reasoning declaration")
    for line_no, line in lines[1:reasoning_index]:
        if not RESOURCE_DECLARATION_PATTERN.fullmatch(line):
            raise FlowSyntaxError(
                f"line {line_no}: invalid resource declaration before reasoning block"
            )
    if lines[-1][1] != "}":
        raise FlowSyntaxError(f"line {lines[-1][0]}: flow must end with '}}'")

    statements = [SourceStatement(lines[0][0], lines[0][0], lines[0][1])]
    statements.extend(
        SourceStatement(line_no, line_no, line)
        for line_no, line in lines[1:reasoning_index]
    )
    statements.append(
        SourceStatement(
            lines[reasoning_index][0],
            lines[reasoning_index][0],
            lines[reasoning_index][1],
        )
    )
    current: List[Tuple[int, str]] = []
    statement_start = re.compile(
        rf"^(?:(?:goal|steps|repeat|on)(?:\s|$)|"
        rf"{ID_PATTERN}\s+(?:<-(?:read|lookup|query|search|snapshot)-|"
        rf"-(?:persist|append|put|upsert|checkpoint|invalidate|promote|commit)->))"
    )
    for line_no, line in lines[reasoning_index + 1 : -1]:
        if statement_start.match(line) and current:
            statements.append(
                SourceStatement(
                    start_line=current[0][0],
                    end_line=current[-1][0],
                    text=" ".join(
                        re.sub(r"\s*\.\.\.\s*$", "", value).strip()
                        for _, value in current
                    ),
                )
            )
            current = []
        current.append((line_no, line))
    if current:
        statements.append(
            SourceStatement(
                start_line=current[0][0],
                end_line=current[-1][0],
                text=" ".join(
                    re.sub(r"\s*\.\.\.\s*$", "", value).strip() for _, value in current
                ),
            )
        )
    statements.append(SourceStatement(lines[-1][0], lines[-1][0], lines[-1][1]))
    return statements


def parse_document(text: str) -> Flow:
    statements = scan_document_statements(text)
    reasoning_index = next(
        (
            index
            for index, statement in enumerate(statements)
            if re.fullmatch(rf"reasoning\s+({ID_PATTERN})\s*\{{", statement.text)
        ),
        None,
    )
    if reasoning_index is None:
        raise FlowSyntaxError("document has no reasoning declaration")
    reasoning_match = re.fullmatch(
        rf"reasoning\s+({ID_PATTERN})\s*\{{", statements[reasoning_index].text
    )
    if not reasoning_match:
        raise FlowSyntaxError(
            f"line {statements[reasoning_index].start_line}: invalid reasoning declaration"
        )

    resources: List[ResourceBinding] = []
    for statement in statements[1:reasoning_index]:
        match = RESOURCE_DECLARATION_PATTERN.fullmatch(statement.text)
        if not match:
            raise FlowSyntaxError(
                f"line {statement.start_line}: invalid resource declaration"
            )
        resources.append(
            ResourceBinding(
                resource_class=match.group("resource_class"),
                alias=match.group("alias"),
                connector=match.group("connector"),
                target=match.group("target"),
                line=statement.start_line,
            )
        )

    goal_text = ""
    goal_handle = ""
    route: Optional[Node] = None
    repeats: List[RepeatBlock] = []
    handlers: List[Handler] = []
    resource_edges: List[ResourceEdge] = []
    for statement in statements[reasoning_index + 1 : -1]:
        line_no = statement.start_line
        line = statement.text
        expression_location: int | str = (
            line_no
            if statement.start_line == statement.end_line
            else f"{statement.start_line}-{statement.end_line}"
        )
        goal_match = re.fullmatch(rf'goal\s+"(.*)"\s*->\s*({ID_PATTERN})', line)
        if goal_match:
            if goal_handle:
                raise FlowSyntaxError(f"line {line_no}: duplicate goal declaration")
            goal_text, goal_handle = goal_match.groups()
            continue
        if line.startswith("route ") or line == "route":
            raise FlowSyntaxError(
                f"line {line_no}: legacy 'route' statement is forbidden; use 'steps'"
            )
        if line.startswith("steps "):
            if route is not None:
                raise FlowSyntaxError(f"line {line_no}: duplicate steps declaration")
            route = ExpressionParser(line[6:].strip(), line=expression_location).parse()
            continue
        repeat_match = re.fullmatch(
            rf"repeat\s+(\d+)\.\.(\d+)\s+\[(.*)\]\s+until\s+({ID_PATTERN})\.({ID_PATTERN})\s+measure\s+({ID_PATTERN})",
            line,
        )
        if repeat_match:
            minimum, maximum, expression, subject, status, measure = (
                repeat_match.groups()
            )
            repeats.append(
                RepeatBlock(
                    minimum=int(minimum),
                    maximum=int(maximum),
                    expression=ExpressionParser(
                        expression, line=expression_location
                    ).parse(),
                    predicate_subject=subject,
                    predicate_status=status,
                    measure=measure,
                    line=line_no,
                )
            )
            continue
        access_match = RESOURCE_ACCESS_PATTERN.fullmatch(line)
        if access_match:
            resource_edges.append(
                ResourceEdge(
                    occurrence_alias=access_match.group("occurrence"),
                    mode=access_match.group("mode"),
                    resource_alias=access_match.group("resource"),
                    direction="read",
                    line=line_no,
                )
            )
            continue
        persist_match = RESOURCE_PERSIST_PATTERN.fullmatch(line)
        if persist_match:
            resource_edges.append(
                ResourceEdge(
                    occurrence_alias=persist_match.group("occurrence"),
                    mode=persist_match.group("mode"),
                    resource_alias=persist_match.group("resource"),
                    direction="write",
                    line=line_no,
                )
            )
            continue
        handler_match = re.fullmatch(
            rf"on\s+({ID_PATTERN})\.({ID_PATTERN})\s*=>\s*(stop|accept|switch\s+@({ID_PATTERN}))",
            line,
        )
        if handler_match:
            subject, status, raw_action, target = handler_match.groups()
            handlers.append(
                Handler(
                    subject=subject,
                    status=status,
                    action="switch" if raw_action.startswith("switch") else raw_action,
                    target=target,
                    line=line_no,
                )
            )
            continue
        if line.startswith("repeat ") and " measure " not in line:
            raise FlowSyntaxError(
                f"line {line_no}: repeat must be bounded and declare 'measure <id>'"
            )
        raise FlowSyntaxError(
            f"line {line_no}: unrecognized reasoning statement {line!r}"
        )

    if not goal_handle:
        raise FlowSyntaxError("reasoning block has no goal declaration")
    if route is None:
        raise FlowSyntaxError("reasoning block has no steps declaration")
    if not handlers:
        raise FlowSyntaxError("reasoning block has no terminal or switch handler")
    return Flow(
        name=reasoning_match.group(1),
        goal_text=goal_text,
        goal_handle=goal_handle,
        route=route,
        repeats=repeats,
        handlers=handlers,
        resources=resources,
        resource_edges=resource_edges,
    )


def occurrences(node: Node) -> List[Occurrence]:
    if isinstance(node, Occurrence):
        return [node]
    result: List[Occurrence] = []
    for child in node.children:
        result.extend(occurrences(child))
    return result


def entry_occurrences(node: Node) -> List[Occurrence]:
    if isinstance(node, Occurrence):
        return [node]
    if isinstance(node, SequenceNode):
        return entry_occurrences(node.children[0])
    result: List[Occurrence] = []
    for child in node.children:
        result.extend(entry_occurrences(child))
    return result


def exit_occurrences(node: Node) -> List[Occurrence]:
    if isinstance(node, Occurrence):
        return [node]
    if isinstance(node, SequenceNode):
        return exit_occurrences(node.children[-1])
    result: List[Occurrence] = []
    for child in node.children:
        result.extend(exit_occurrences(child))
    return result


def output_signature(node: Node) -> Set[Tuple[str, Optional[str]]]:
    return {
        (port.name, port.root_kind)
        for occurrence in exit_occurrences(node)
        for port in occurrence.outputs
    }


def finding(
    code: str, message: str, *, severity: str = "error", line: Optional[int] = None
) -> Dict[str, Any]:
    result: Dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if line is not None:
        result["line"] = line
    return result


def validate_expression(
    node: Node,
    *,
    registry: Dict[str, Any],
    findings: List[Dict[str, Any]],
) -> None:
    operation_types = registry["operation_types"]
    relations = registry["relations"]
    allowed_kinds = set(registry["semantic_kinds"]) | set(registry["interface_kinds"])

    for occurrence in occurrences(node):
        if occurrence.type_code != "_" and occurrence.type_code not in operation_types:
            findings.append(
                finding(
                    "unknown_operation_type",
                    f"Occurrence {occurrence.alias!r} uses unknown type {occurrence.type_code!r}.",
                )
            )
        for port in [*occurrence.inputs, *occurrence.outputs]:
            if port.root_kind is not None and port.root_kind not in allowed_kinds:
                findings.append(
                    finding(
                        "unknown_port_kind",
                        f"Port {port.name!r} uses unknown semantic kind {port.root_kind!r}.",
                    )
                )

    if isinstance(node, Choice):
        expected = output_signature(node.children[0])
        for branch_index, branch in enumerate(node.children[1:], 2):
            actual = output_signature(branch)
            if actual != expected:
                findings.append(
                    finding(
                        "alternative_interface_mismatch",
                        "Alternative branch "
                        f"{branch_index} exposes {sorted(actual)} instead of {sorted(expected)}.",
                    )
                )
    if isinstance(node, SequenceNode):
        for index, relation_name in enumerate(node.relations):
            left = node.children[index]
            right = node.children[index + 1]
            relation = relations.get(relation_name)
            if relation is None:
                findings.append(
                    finding(
                        "unknown_relation",
                        f"Transition uses unknown relation {relation_name!r}.",
                    )
                )
                continue
            left_outputs = {
                port.name
                for occurrence in exit_occurrences(left)
                for port in occurrence.outputs
            }
            right_inputs = {
                port.name
                for occurrence in entry_occurrences(right)
                for port in occurrence.inputs
            }
            if not left_outputs.intersection(right_inputs):
                findings.append(
                    finding(
                        "handle_not_conserved",
                        f"Relation {relation_name!r} conserves no handle: "
                        f"left outputs {sorted(left_outputs)}, right inputs {sorted(right_inputs)}.",
                    )
                )
            for source_occurrence in exit_occurrences(left):
                source_outputs = {port.name for port in source_occurrence.outputs}
                if not source_outputs.intersection(right_inputs):
                    findings.append(
                        finding(
                            "parallel_contribution_not_conserved",
                            f"Required branch {source_occurrence.alias!r} contributes no "
                            f"handle across relation {relation_name!r}.",
                        )
                    )
            for target_occurrence in entry_occurrences(right):
                target_inputs = {port.name for port in target_occurrence.inputs}
                if not left_outputs.intersection(target_inputs):
                    findings.append(
                        finding(
                            "parallel_consumer_not_grounded",
                            f"Required branch {target_occurrence.alias!r} consumes no "
                            f"handle from relation {relation_name!r}.",
                        )
                    )
            target_types = set(relation.get("target_types", []))
            actual_targets = {
                occurrence.type_code for occurrence in entry_occurrences(right)
            }
            if target_types and not actual_targets.issubset(target_types):
                findings.append(
                    finding(
                        "relation_target_mismatch",
                        f"Relation {relation_name!r} targets {sorted(actual_targets)}; "
                        f"allowed targets are {sorted(target_types)}.",
                    )
                )
            if relation.get("same_type"):
                source_types = {
                    occurrence.type_code for occurrence in exit_occurrences(left)
                }
                if source_types != actual_targets:
                    findings.append(
                        finding(
                            "preservation_type_mismatch",
                            f"Preservation changes type from {sorted(source_types)} to {sorted(actual_targets)}.",
                        )
                    )

    if not isinstance(node, Occurrence):
        for child in node.children:
            validate_expression(child, registry=registry, findings=findings)


def validate_flow(
    flow: Flow, *, registry: Dict[str, Any], strict: bool
) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    validate_expression(flow.route, registry=registry, findings=findings)
    for repeat in flow.repeats:
        validate_expression(repeat.expression, registry=registry, findings=findings)

    all_occurrences = occurrences(flow.route)
    for repeat in flow.repeats:
        all_occurrences.extend(occurrences(repeat.expression))

    aliases: Dict[str, Occurrence] = {}
    for occurrence in all_occurrences:
        if occurrence.alias in aliases:
            findings.append(
                finding(
                    "duplicate_occurrence_alias",
                    f"Occurrence alias {occurrence.alias!r} is not unique in the flow.",
                )
            )
        aliases[occurrence.alias] = occurrence

    resources: Dict[str, ResourceBinding] = {}
    for resource in flow.resources:
        if resource.alias in resources:
            findings.append(
                finding(
                    "duplicate_resource_alias",
                    f"Resource alias {resource.alias!r} is not unique.",
                    line=resource.line,
                )
            )
        if resource.alias in aliases:
            findings.append(
                finding(
                    "resource_occurrence_alias_collision",
                    f"Resource alias {resource.alias!r} collides with an occurrence alias.",
                    line=resource.line,
                )
            )
        target_parts = Path(resource.target).parts
        if (
            Path(resource.target).is_absolute()
            or ".." in target_parts
            or "://" in resource.target
            or re.match(r"^[A-Za-z]:[\\/]", resource.target)
        ):
            findings.append(
                finding(
                    "unsafe_resource_target",
                    f"Resource target {resource.target!r} must be repository-relative "
                    "and cannot contain traversal or a network endpoint.",
                    line=resource.line,
                )
            )
        resources[resource.alias] = resource

    for occurrence in all_occurrences:
        resource_outputs = sorted(
            port.name for port in occurrence.outputs if port.name in resources
        )
        if resource_outputs:
            findings.append(
                finding(
                    "resource_alias_as_epistemic_output",
                    f"Occurrence {occurrence.alias!r} produces resource aliases "
                    f"{resource_outputs}; resources may only be declared externally.",
                )
            )

    accessed_resources: Set[str] = set()
    resource_inputs = {
        port.name
        for occurrence in all_occurrences
        for port in occurrence.inputs
        if port.name in resources
    }
    edges_by_pair: Set[Tuple[str, str, str]] = set()
    terminal_aliases = {occurrence.alias for occurrence in exit_occurrences(flow.route)}
    for repeat in flow.repeats:
        terminal_aliases.update(
            occurrence.alias for occurrence in exit_occurrences(repeat.expression)
        )
    for edge in flow.resource_edges:
        edge_key = (edge.occurrence_alias, edge.direction, edge.resource_alias)
        if edge_key in edges_by_pair:
            findings.append(
                finding(
                    "duplicate_resource_edge",
                    f"Resource edge {edge.occurrence_alias!r} {edge.direction} "
                    f"{edge.resource_alias!r} is duplicated.",
                    line=edge.line,
                )
            )
        edges_by_pair.add(edge_key)
        occurrence = aliases.get(edge.occurrence_alias)
        resource = resources.get(edge.resource_alias)
        if occurrence is None:
            findings.append(
                finding(
                    "unknown_resource_edge_occurrence",
                    f"Resource edge references unknown occurrence {edge.occurrence_alias!r}.",
                    line=edge.line,
                )
            )
            continue
        if resource is None:
            findings.append(
                finding(
                    "unknown_resource_alias",
                    f"Resource edge references undeclared resource {edge.resource_alias!r}.",
                    line=edge.line,
                )
            )
            continue
        accessed_resources.add(resource.alias)
        if edge.direction == "read":
            input_names = {port.name for port in occurrence.inputs}
            if resource.alias not in input_names:
                findings.append(
                    finding(
                        "resource_not_consumed",
                        f"Read edge requires occurrence {occurrence.alias!r} to consume "
                        f"resource handle {resource.alias!r} explicitly.",
                        line=edge.line,
                    )
                )
            if resource.resource_class == "SEARCH" and edge.mode not in {
                "read",
                "query",
                "search",
                "snapshot",
            }:
                findings.append(
                    finding(
                        "resource_mode_mismatch",
                        f"SEARCH resource {resource.alias!r} does not license {edge.mode!r}.",
                        line=edge.line,
                    )
                )
        else:
            if resource.resource_class == "SEARCH":
                findings.append(
                    finding(
                        "search_resource_write_forbidden",
                        f"SEARCH resource {resource.alias!r} is read-only.",
                        line=edge.line,
                    )
                )
            if occurrence.type_code != "E":
                findings.append(
                    finding(
                        "uncalibrated_persistence",
                        f"Persistence must be authorized by an E occurrence, not "
                        f"{occurrence.alias}:{occurrence.type_code}.",
                        line=edge.line,
                    )
                )
            elif occurrence.alias not in terminal_aliases:
                findings.append(
                    finding(
                        "nonterminal_persistence",
                        f"Persistence occurrence {occurrence.alias!r} must terminate "
                        "the steps expression or a bounded repeat body.",
                        line=edge.line,
                    )
                )

    for resource_alias in sorted(resource_inputs):
        if not any(
            edge.direction == "read" and edge.resource_alias == resource_alias
            for edge in flow.resource_edges
        ):
            findings.append(
                finding(
                    "undeclared_resource_consumption",
                    f"Resource handle {resource_alias!r} is consumed without an inverted access edge.",
                )
            )
    unused_resources = sorted(set(resources) - accessed_resources)
    for resource_alias in unused_resources:
        findings.append(
            finding(
                "unused_resource_binding",
                f"Resource {resource_alias!r} is bound but has no access or persistence edge.",
                severity="warning",
                line=resources[resource_alias].line,
            )
        )

    kind_by_handle: Dict[str, str] = {}
    for occurrence in all_occurrences:
        for port in [*occurrence.inputs, *occurrence.outputs]:
            if port.root_kind is None:
                continue
            previous = kind_by_handle.get(port.name)
            if previous is not None and previous != port.root_kind:
                findings.append(
                    finding(
                        "handle_kind_mismatch",
                        f"Handle {port.name!r} changes kind from {previous!r} to {port.root_kind!r}.",
                    )
                )
            kind_by_handle[port.name] = port.root_kind

    route_exits = exit_occurrences(flow.route)
    if any(occurrence.type_code != "E" for occurrence in route_exits):
        findings.append(
            finding(
                "uncalibrated_route_terminal",
                "Every route branch must terminate in an E calibration occurrence.",
            )
        )
    goal_outputs = {
        port.name for occurrence in route_exits for port in occurrence.outputs
    }
    if flow.goal_handle not in goal_outputs:
        findings.append(
            finding(
                "goal_handle_not_produced",
                f"Goal handle {flow.goal_handle!r} is not produced by terminal calibration.",
            )
        )
    if kind_by_handle.get(flow.goal_handle) not in {None, "Decision"}:
        findings.append(
            finding(
                "goal_handle_not_decision",
                f"Goal handle {flow.goal_handle!r} must have semantic kind Decision when typed.",
            )
        )

    for repeat in flow.repeats:
        if repeat.minimum < 0 or repeat.maximum < repeat.minimum or repeat.maximum > 32:
            findings.append(
                finding(
                    "invalid_repeat_bound",
                    f"Repeat bound {repeat.minimum}..{repeat.maximum} must satisfy 0 <= min <= max <= 32.",
                    line=repeat.line,
                )
            )
        repeat_exits = exit_occurrences(repeat.expression)
        if any(occurrence.type_code != "E" for occurrence in repeat_exits):
            findings.append(
                finding(
                    "uncalibrated_repeat_terminal",
                    "Every repeat branch must terminate in an E calibration occurrence.",
                    line=repeat.line,
                )
            )
        repeat_aliases = {
            occurrence.alias: occurrence
            for occurrence in occurrences(repeat.expression)
        }
        predicate_occurrence = repeat_aliases.get(repeat.predicate_subject)
        if predicate_occurrence is None or predicate_occurrence.type_code != "E":
            findings.append(
                finding(
                    "invalid_repeat_predicate",
                    "Repeat termination predicate must reference an E occurrence inside its body.",
                    line=repeat.line,
                )
            )

    has_gap = any(occurrence.type_code == "_" for occurrence in all_occurrences)
    for handler in flow.handlers:
        if handler.subject == "flow":
            findings.append(
                finding(
                    "legacy_flow_predicate",
                    "Legacy handler subject 'flow' is forbidden; use 'reasoning'.",
                    line=handler.line,
                )
            )
            continue
        if handler.subject == "reasoning":
            if handler.action != "stop":
                findings.append(
                    finding(
                        "reasoning_predicate_authority",
                        "A reasoning-level predicate may stop but may not accept or switch programs.",
                        line=handler.line,
                    )
                )
            continue
        predicate_occurrence = aliases.get(handler.subject)
        if predicate_occurrence is None:
            findings.append(
                finding(
                    "unknown_handler_occurrence",
                    f"Handler references unknown occurrence {handler.subject!r}.",
                    line=handler.line,
                )
            )
            continue
        if (
            handler.action in {"accept", "switch"}
            and predicate_occurrence.type_code != "E"
        ):
            findings.append(
                finding(
                    "uncalibrated_terminal_authority",
                    f"{handler.action} must be guarded by an E occurrence.",
                    line=handler.line,
                )
            )
        if has_gap and handler.action == "accept":
            findings.append(
                finding(
                    "gap_bearing_flow_accepts",
                    "A flow containing an unresolved '_' projection gap cannot accept.",
                    line=handler.line,
                )
            )

    severity_blockers = {"error"}
    if strict:
        severity_blockers.add("warning")
    ok = not any(item["severity"] in severity_blockers for item in findings)
    return {
        "name": flow.name,
        "ok": ok,
        "projection_status": (
            "gap_bearing_descriptive" if has_gap else "coherent_profile"
        ),
        "executable_projection": not has_gap,
        "operation_count": len(all_occurrences),
        "repeat_count": len(flow.repeats),
        "handler_count": len(flow.handlers),
        "resource_count": len(flow.resources),
        "resource_edge_count": len(flow.resource_edges),
        "goal_handle": flow.goal_handle,
        "findings": findings,
    }


def load_registry(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FlowSyntaxError(f"semantic registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FlowSyntaxError(f"semantic registry is invalid JSON: {exc}") from exc
    required = {
        "language_version",
        "reference_alignment",
        "surface_syntax",
        "operation_types",
        "semantic_kinds",
        "interface_kinds",
        "relations",
        "resource_plane",
    }
    missing = sorted(required - set(value))
    if missing:
        raise FlowSyntaxError(f"semantic registry is missing keys: {missing}")
    return value


def yaml_section_ids(path: Path, section: str) -> Set[str]:
    """Read ids or mapping keys from one top-level YAML section conservatively."""
    values: Set[str] = set()
    active = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if (
            raw_line
            and not raw_line.startswith(" ")
            and raw_line.rstrip().endswith(":")
        ):
            active = raw_line.rstrip() == f"{section}:"
            continue
        if not active:
            continue
        item_match = re.match(r"^  - id:\s*([a-z][a-z0-9_]*)\s*$", raw_line)
        if item_match:
            values.add(item_match.group(1))
            continue
        key_match = re.match(r"^  ([a-z][a-z0-9_]*):(?:\s.*)?$", raw_line)
        if key_match:
            values.add(key_match.group(1))
    return values


def validate_registries(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    surface = registry["surface_syntax"]
    if (
        surface.get("program_keyword") != "reasoning"
        or surface.get("steps_keyword") != "steps"
        or surface.get("projection_keyword") != "map"
        or surface.get("continuation_marker") != "..."
        or set(surface.get("legacy_keywords_rejected", [])) != {"flow", "route"}
        or not re.fullmatch(r"[0-9a-f]{64}", str(surface.get("source_sha256", "")))
    ):
        findings.append(
            finding(
                "surface_syntax_alignment",
                "Canonical ERFL 0.3 syntax must use reasoning/steps/..., with flow/route rejected.",
            )
        )
    resource_plane = registry["resource_plane"]
    if (
        set(resource_plane.get("classes", [])) != {"KB", "SEARCH", "STORE"}
        or set(resource_plane.get("read_modes", []))
        != {"read", "lookup", "query", "search", "snapshot"}
        or set(resource_plane.get("write_modes", []))
        != {
            "persist",
            "append",
            "put",
            "upsert",
            "checkpoint",
            "invalidate",
            "promote",
            "commit",
        }
    ):
        findings.append(
            finding(
                "resource_plane_alignment",
                "The ERFL resource-plane classes or access/effect modes are incomplete.",
            )
        )
    reference = registry["reference_alignment"]
    archive_digest = reference.get("source_archive_sha256", "")
    member_digests = reference.get("source_members", {})
    invalid_member_digests = sorted(
        name
        for name, digest in member_digests.items()
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest))
    )
    if (
        reference.get("reference_version") != "0.2"
        or not re.fullmatch(r"[0-9a-f]{64}", str(archive_digest))
        or not member_digests
        or invalid_member_digests
    ):
        findings.append(
            finding(
                "reference_provenance_alignment",
                "ERFL reference provenance is incomplete or malformed: "
                f"version={reference.get('reference_version')!r}, "
                f"archive_digest_valid={bool(re.fullmatch(r'[0-9a-f]{64}', str(archive_digest)))}, "
                f"member_count={len(member_digests)}, "
                f"invalid_member_digests={invalid_member_digests}.",
            )
        )

    core_operations = set(reference.get("core_operation_codes", []))
    missing_core_operations = sorted(core_operations - set(registry["operation_types"]))
    adaptation_operations = set(reference.get("operation_adaptation", {}))
    missing_operation_adaptations = sorted(core_operations - adaptation_operations)
    extra_operation_adaptations = sorted(adaptation_operations - core_operations)
    if (
        missing_core_operations
        or missing_operation_adaptations
        or extra_operation_adaptations
    ):
        findings.append(
            finding(
                "reference_operation_alignment",
                "ERFL 0.2 operation alignment is incomplete: "
                f"missing_codes={missing_core_operations}, "
                f"missing_adaptations={missing_operation_adaptations}, "
                f"extra_adaptations={extra_operation_adaptations}.",
            )
        )

    declared_operation_extensions = set(
        reference.get("mathformer_operation_extensions", {})
    )
    actual_operation_extensions = set(registry["operation_types"]) - core_operations
    if declared_operation_extensions != actual_operation_extensions:
        findings.append(
            finding(
                "reference_operation_extension_alignment",
                "Mathformer operation extensions do not match the declared adaptation: "
                f"undeclared={sorted(actual_operation_extensions - declared_operation_extensions)}, "
                f"unimplemented={sorted(declared_operation_extensions - actual_operation_extensions)}.",
            )
        )

    core_relations = set(reference.get("core_relations", []))
    missing_core_relations = sorted(core_relations - set(registry["relations"]))
    if missing_core_relations:
        findings.append(
            finding(
                "reference_relation_alignment",
                "ERFL 0.2 core relations are missing from the Mathformer profile: "
                f"{missing_core_relations}.",
            )
        )

    declared_relation_extensions = set(
        reference.get("mathformer_relation_extensions", [])
    )
    actual_relation_extensions = set(registry["relations"]) - core_relations
    if declared_relation_extensions != actual_relation_extensions:
        findings.append(
            finding(
                "reference_relation_extension_alignment",
                "Mathformer relation extensions do not match the declared adaptation: "
                f"undeclared={sorted(actual_relation_extensions - declared_relation_extensions)}, "
                f"unimplemented={sorted(declared_relation_extensions - actual_relation_extensions)}.",
            )
        )

    required_combinators = {
        "labelled_sequence",
        "alternative",
        "parallel_product",
        "optional_occurrence",
        "bounded_repeat",
        "terminal_handler",
        "workflow_switch",
        "projection_gap",
    }
    declared_combinators = set(reference.get("core_combinators", []))
    if declared_combinators != required_combinators:
        findings.append(
            finding(
                "reference_combinator_alignment",
                "ERFL reference combinator declaration is incomplete: "
                f"missing={sorted(required_combinators - declared_combinators)}, "
                f"extra={sorted(declared_combinators - required_combinators)}.",
            )
        )

    reasoning_ids = yaml_section_ids(REASONING_REGISTRY, "primitive_types")
    referenced_reasoning_ids = {
        value["reasoning_primitive"] for value in registry["operation_types"].values()
    }
    missing_reasoning = sorted(referenced_reasoning_ids - reasoning_ids)
    if missing_reasoning:
        findings.append(
            finding(
                "reasoning_registry_mismatch",
                f"ERFL references reasoning primitives absent from REASONING_TYPES.yaml: {missing_reasoning}.",
            )
        )

    output_kinds = yaml_section_ids(OUTPUT_REGISTRY, "semantic_kinds")
    referenced_output_kinds = {name.lower() for name in registry["semantic_kinds"]}
    missing_output_kinds = sorted(referenced_output_kinds - output_kinds)
    if missing_output_kinds:
        findings.append(
            finding(
                "output_registry_mismatch",
                f"ERFL semantic kinds absent from OUTPUT_TYPES.yaml: {missing_output_kinds}.",
            )
        )

    output_types = yaml_section_ids(OUTPUT_REGISTRY, "output_types")
    semantic_contracts = yaml_section_ids(
        OUTPUT_REGISTRY, "output_type_semantic_kind_contracts"
    )
    missing_semantic_contracts = sorted(output_types - semantic_contracts)
    extra_semantic_contracts = sorted(semantic_contracts - output_types)
    if missing_semantic_contracts or extra_semantic_contracts:
        findings.append(
            finding(
                "output_semantic_contract_coverage",
                "Output-type semantic-kind contracts are not exhaustive: "
                f"missing={missing_semantic_contracts}, extra={extra_semantic_contracts}.",
            )
        )

    reasoning_defaults = yaml_section_ids(
        OUTPUT_REGISTRY, "reasoning_type_output_defaults"
    )
    missing_reasoning_defaults = sorted(reasoning_ids - reasoning_defaults)
    extra_reasoning_defaults = sorted(reasoning_defaults - reasoning_ids)
    if missing_reasoning_defaults or extra_reasoning_defaults:
        findings.append(
            finding(
                "reasoning_output_default_coverage",
                "Reasoning-to-output defaults are not exhaustive: "
                f"missing={missing_reasoning_defaults}, extra={extra_reasoning_defaults}.",
            )
        )

    reasoning_styles = yaml_section_ids(REASONING_REGISTRY, "reasoning_styles")
    profile_names: Set[str] = set()
    for profile_path in sorted(
        (REPO_ROOT / "examples" / "reasoning_flows").glob("*.rflow")
    ):
        try:
            profile_names.add(
                parse_document(profile_path.read_text(encoding="utf-8")).name
            )
        except FlowSyntaxError as exc:
            findings.append(
                finding(
                    "reasoning_profile_syntax_error",
                    f"{profile_path.relative_to(REPO_ROOT)}: {exc}",
                )
            )
    missing_profiles = sorted(reasoning_styles - profile_names)
    extra_profiles = sorted(profile_names - reasoning_styles)
    if missing_profiles or extra_profiles:
        findings.append(
            finding(
                "reasoning_style_profile_coverage",
                "Reasoning-style flow profiles are not one-to-one with the registry: "
                f"missing={missing_profiles}, extra={extra_profiles}.",
            )
        )
    return findings


def validate_text(
    text: str,
    *,
    source: str,
    registry: Dict[str, Any],
    strict: bool,
) -> Dict[str, Any]:
    try:
        flow = parse_document(text)
    except FlowSyntaxError as exc:
        return {
            "source": source,
            "ok": False,
            "projection_status": "invalid",
            "findings": [finding("syntax_error", str(exc))],
        }
    report = validate_flow(flow, registry=registry, strict=strict)
    report["source"] = source
    return report


def run_self_test(registry: Dict[str, Any]) -> Dict[str, Any]:
    valid = """erfl 0.3
reasoning valid_flow {
  goal "produce a calibrated result" -> status
  steps a:A[gap::Context->candidate::Claim] -assume> d:D[candidate::Claim->claim::Claim] -test> p:P[claim::Claim->evidence::Evidence] -assess> r:R[claim::Claim,evidence::Evidence->assessment::Assessment] -calibrate> e:E[claim::Claim,assessment::Assessment->status::Decision]
  on e.accepted => accept
  on e.blocked => stop
}
"""
    multiline_valid = """erfl 0.3
reasoning multiline_valid_flow {
  goal "produce a calibrated repaired result"
    -> status
  steps
    a:A[gap::Context->candidate::Claim] -assume> ...
    d:D[candidate::Claim->claim::Claim] -test> ...
    p:P[claim::Claim->evidence::Evidence] -assess> ...
    r:R[
      claim::Claim,
      evidence::Evidence
      -> assessment::Assessment
    ] -calibrate> ...
    e:E[
      claim::Claim,
      assessment::Assessment
      -> status::Decision
    ]
  repeat 1..2 [
    x:X[claim::Claim,assessment::Assessment->repair::Plan]
    -revise> f:F[claim::Claim,repair::Plan->candidate2::Bundle]
    -test> p2:P[candidate2::Bundle->evidence2::Evidence]
    -assess> r2:R[
      candidate2::Bundle,
      evidence2::Evidence
      -> assessment2::Assessment
    ]
    -calibrate> e2:E[
      candidate2::Bundle,
      assessment2::Assessment
      -> iteration_status::Decision
    ]
  ] until e2.accepted
    measure unresolved_findings
  on e.accepted => accept
  on e.blocked => stop
}
"""
    cases = [
        ("valid", valid, True, None),
        ("multiline_layout", multiline_valid, True, None),
        (
            "legacy_edge",
            valid.replace(" -assume> ", " > "),
            False,
            "syntax_error",
        ),
        (
            "legacy_flow_keyword",
            valid.replace("reasoning valid_flow", "flow valid_flow"),
            False,
            "syntax_error",
        ),
        (
            "legacy_route_keyword",
            valid.replace("  steps ", "  route "),
            False,
            "syntax_error",
        ),
        (
            "handle_loss",
            valid.replace("d:D[candidate::Claim", "d:D[other::Claim"),
            False,
            "handle_not_conserved",
        ),
        (
            "uncalibrated_terminal",
            valid.replace(
                " -calibrate> e:E[claim::Claim,assessment::Assessment->status::Decision]",
                "",
            )
            .replace("on e.accepted", "on r.accepted")
            .replace("on e.blocked", "on r.blocked"),
            False,
            "uncalibrated_route_terminal",
        ),
        (
            "uncalibrated_accept",
            valid.replace("on e.accepted", "on r.accepted"),
            False,
            "uncalibrated_terminal_authority",
        ),
        (
            "repeat_without_measure",
            valid.replace(
                "  on e.accepted",
                "  repeat 1..2 [x:X[claim::Claim,assessment::Assessment->repair::Plan] -revise> f:F[claim::Claim,repair::Plan->candidate2::Bundle] -test> p2:P[candidate2::Bundle->evidence2::Evidence] -assess> r2:R[candidate2::Bundle,evidence2::Evidence->assessment2::Assessment] -calibrate> e2:E[candidate2::Bundle,assessment2::Assessment->iteration_status::Decision]] until e2.accepted\n  on e.accepted",
            ),
            False,
            "syntax_error",
        ),
        (
            "gap_acceptance",
            valid.replace("a:A", "a:_"),
            False,
            "gap_bearing_flow_accepts",
        ),
        (
            "choice_interface",
            valid.replace(
                "a:A[gap::Context->candidate::Claim]",
                "(a:A[gap::Context->candidate::Claim] | i:I[gap::Context->pattern::Claim])",
            ),
            False,
            "alternative_interface_mismatch",
        ),
        (
            "parallel_contribution_loss",
            valid.replace(
                "a:A[gap::Context->candidate::Claim]",
                "(a:A[gap::Context->candidate::Claim] & i:I[gap::Context->pattern::Claim])",
            ),
            False,
            "parallel_contribution_not_conserved",
        ),
        (
            "resource_access",
            valid.replace(
                "reasoning valid_flow {",
                '@KB kb0 connect(file("MathformerKB"))\nreasoning valid_flow {',
            )
            .replace(
                "a:A[gap::Context",
                "a:A[kb0,gap::Context",
            )
            .replace(
                "  on e.accepted",
                "  a <-query- kb0\n  on e.accepted",
            ),
            True,
            None,
        ),
        (
            "resource_access_not_consumed",
            valid.replace(
                "reasoning valid_flow {",
                '@KB kb0 connect(file("MathformerKB"))\nreasoning valid_flow {',
            ).replace(
                "  on e.accepted",
                "  a <-query- kb0\n  on e.accepted",
            ),
            False,
            "resource_not_consumed",
        ),
        (
            "uncalibrated_persistence",
            valid.replace(
                "reasoning valid_flow {",
                '@KB kb0 connect(file("MathformerKB"))\nreasoning valid_flow {',
            ).replace(
                "  on e.accepted",
                "  a -persist-> kb0\n  on e.accepted",
            ),
            False,
            "uncalibrated_persistence",
        ),
        (
            "unsafe_resource_target",
            valid.replace(
                "reasoning valid_flow {",
                '@KB kb0 connect(file("../secrets"))\nreasoning valid_flow {',
            ).replace(
                "  on e.accepted",
                "  e -persist-> kb0\n  on e.accepted",
            ),
            False,
            "unsafe_resource_target",
        ),
        (
            "search_resource_write",
            valid.replace(
                "reasoning valid_flow {",
                '@SEARCH search0 connect(file("MathformerKB"))\nreasoning valid_flow {',
            ).replace(
                "  on e.accepted",
                "  e -persist-> search0\n  on e.accepted",
            ),
            False,
            "search_resource_write_forbidden",
        ),
    ]
    results: List[Dict[str, Any]] = []
    for name, text, expected_ok, expected_code in cases:
        report = validate_text(
            text,
            source=f"self-test:{name}",
            registry=registry,
            strict=True,
        )
        codes = {item["code"] for item in report.get("findings", [])}
        passed = report["ok"] is expected_ok and (
            expected_code is None or expected_code in codes
        )
        results.append(
            {
                "id": name,
                "passed": passed,
                "expected_ok": expected_ok,
                "actual_ok": report["ok"],
                "expected_code": expected_code,
                "actual_codes": sorted(codes),
            }
        )
    compact_equivalent = (
        "\n".join(
            statement.text for statement in scan_document_statements(multiline_valid)
        )
        + "\n"
    )
    multiline_signature = asdict(parse_document(multiline_valid))
    compact_signature = asdict(parse_document(compact_equivalent))
    for signature in (multiline_signature, compact_signature):
        for repeat in signature["repeats"]:
            repeat.pop("line", None)
        for handler in signature["handlers"]:
            handler.pop("line", None)
    equivalent = multiline_signature == compact_signature
    results.append(
        {
            "id": "multiline_semantic_equivalence",
            "passed": equivalent,
            "expected_ok": True,
            "actual_ok": equivalent,
            "expected_code": None,
            "actual_codes": [],
        }
    )
    return {
        "ok": all(result["passed"] for result in results),
        "case_count": len(results),
        "passed": sum(result["passed"] for result in results),
        "results": results,
    }


def build_parser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, prog=prog)
    parser.add_argument(
        "paths", nargs="*", type=Path, help="ERFL .rflow files to validate"
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as blocking"
    )
    parser.add_argument(
        "--check-registries",
        action="store_true",
        help="Check ERFL symbols and semantic kinds against framework registries",
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def prepare_validation(args: argparse.Namespace) -> Dict[str, Any]:
    """Load once and select the native dispatch route, in CLI order."""
    values = vars(args).copy()
    values["paths"] = [str(path) for path in args.paths]
    values["registry"] = str(args.registry)
    session = {"args": values}
    try:
        session["registry"] = load_registry(args.registry)
    except FlowSyntaxError as exc:
        session["registry_error"] = str(exc)
        return {"session": session, "route": "registry_error"}
    route = (
        "self_test" if args.self_test else ("files" if args.paths else "argument_error")
    )
    return {"session": session, "route": route}


def validation_early_exit(session: Dict[str, Any]):
    if "registry_error" in session:
        message = session["registry_error"]
        payload = {"ok": False, "findings": [finding("registry_error", message)]}
        print(
            json.dumps(payload, indent=2, sort_keys=True)
            if session["args"]["json"]
            else message
        )
        return 1, payload
    build_parser(prog=session.get("program")).error(
        "provide at least one .rflow path or use --self-test"
    )


def validation_self_test(session: Dict[str, Any]):
    payload = {"schema_version": 1, "self_test": run_self_test(session["registry"])}
    payload["ok"] = payload["self_test"]["ok"]
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if session["args"]["json"]
        else payload
    )
    return (0 if payload["ok"] else 1), payload


def expand_validation(session: Dict[str, Any]) -> Dict[str, Any]:
    expanded_paths: List[Path] = []
    for raw in session["args"]["paths"]:
        path = Path(raw)
        if path.is_dir():
            expanded_paths.extend(sorted(path.glob("*.rflow")))
        else:
            expanded_paths.append(path)
    return {
        "expanded_paths": [str(path) for path in expanded_paths],
        "cursor": 0,
        "reports": [],
        "session": session,
    }


def validate_next_path(state: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(state["expanded_paths"][state["cursor"]])
    if not path.exists():
        report = {
            "source": str(path),
            "ok": False,
            "projection_status": "missing",
            "findings": [finding("flow_file_missing", f"Flow file not found: {path}")],
        }
    else:
        report = validate_text(
            path.read_text(encoding="utf-8"),
            source=str(path),
            registry=state["session"]["registry"],
            strict=state["session"]["args"]["strict"],
        )
    state["reports"].append(report)
    state["cursor"] += 1
    return state


def finish_validation(state: Dict[str, Any]):
    args = state["session"]["args"]
    registry = state["session"]["registry"]
    reports = state["reports"]
    registry_findings = (
        validate_registries(registry) if args["check_registries"] else []
    )
    ok = all(report["ok"] for report in reports) and not registry_findings
    payload = {
        "schema_version": 1,
        "language_version": registry["language_version"],
        "ok": ok,
        "flow_count": len(reports),
        "valid_flow_count": sum(report["ok"] for report in reports),
        "gap_bearing_flow_count": sum(
            report.get("projection_status") == "gap_bearing_descriptive"
            for report in reports
        ),
        "registry_findings": registry_findings,
        "flows": reports,
    }
    if args["json"]:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for report in reports:
            state = "PASS" if report["ok"] else "FAIL"
            print(
                f"{state} {report['source']}: {report.get('projection_status', 'invalid')}"
            )
            for item in report.get("findings", []):
                print(f"  {item['severity']}: {item['code']}: {item['message']}")
        for item in registry_findings:
            print(f"FAIL registry: {item['code']}: {item['message']}")
    return (0 if ok else 1), payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    prepared = prepare_validation(build_parser().parse_args(argv))
    session, route = prepared["session"], prepared["route"]
    if route in ("registry_error", "argument_error"):
        return validation_early_exit(session)[0]
    if route == "self_test":
        return validation_self_test(session)[0]
    state = expand_validation(session)
    while state["cursor"] < len(state["expanded_paths"]):
        state = validate_next_path(state)
    return finish_validation(state)[0]


if __name__ == "__main__":
    sys.exit(main())
