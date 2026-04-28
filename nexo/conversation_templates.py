"""Conversation template schema and parser for chatbot graph extraction.

Defines JSON schema for conversation templates and provides parsing
functions to extract nodes+edges dicts compatible with nexo's build.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class IntentNode:
    """Represents an intent detection node."""
    id: str
    label: str
    triggers: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.7
    description: str = ""


@dataclass
class ResponseNode:
    """Represents a response template node."""
    id: str
    label: str
    templates: list[str] = field(default_factory=list)
    tone: str = "neutral"
    context: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class StateNode:
    """Represents a state collection node."""
    id: str
    label: str
    required_slots: list[str] = field(default_factory=list)
    optional_slots: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class FailureStateNode:
    """Represents a failure state with recovery path."""
    id: str
    label: str
    recovery_path: str = ""
    max_retries: int = 2
    description: str = ""


@dataclass
class ConversationEdge:
    """Represents an edge between conversation nodes."""
    source: str
    target: str
    relation: str = "leads_to"
    condition: str | None = None
    weight: float = 1.0


@dataclass
class ConversationTemplate:
    """A complete conversation template with nodes and edges."""
    id: str
    name: str = ""
    description: str = ""
    nodes: list[IntentNode | ResponseNode | StateNode | FailureStateNode] = field(default_factory=list)
    edges: list[ConversationEdge] = field(default_factory=list)


def _parse_node(node_data: dict[str, Any]) -> IntentNode | ResponseNode | StateNode | FailureStateNode:
    """Parse a node dict into the appropriate node class."""
    node_type = node_data.get("type", "state")

    if node_type == "intent":
        return IntentNode(
            id=node_data.get("id", ""),
            label=node_data.get("label", ""),
            triggers=node_data.get("triggers", []),
            confidence_threshold=node_data.get("confidence_threshold", 0.7),
            description=node_data.get("description", ""),
        )
    elif node_type == "response":
        return ResponseNode(
            id=node_data.get("id", ""),
            label=node_data.get("label", ""),
            templates=node_data.get("templates", []),
            tone=node_data.get("tone", "neutral"),
            context=node_data.get("context", []),
            description=node_data.get("description", ""),
        )
    elif node_type == "failure_state":
        return FailureStateNode(
            id=node_data.get("id", ""),
            label=node_data.get("label", ""),
            recovery_path=node_data.get("recovery_path", ""),
            max_retries=node_data.get("max_retries", 2),
            description=node_data.get("description", ""),
        )
    else:  # state
        return StateNode(
            id=node_data.get("id", ""),
            label=node_data.get("label", ""),
            required_slots=node_data.get("required_slots", []),
            optional_slots=node_data.get("optional_slots", []),
            description=node_data.get("description", ""),
        )


def _parse_edge(edge_data: dict[str, Any]) -> ConversationEdge:
    """Parse an edge dict into a ConversationEdge."""
    return ConversationEdge(
        source=edge_data.get("source", ""),
        target=edge_data.get("target", ""),
        relation=edge_data.get("relation", "leads_to"),
        condition=edge_data.get("condition"),
        weight=edge_data.get("weight", 1.0),
    )


def parse_conversation_template(data: dict[str, Any]) -> ConversationTemplate:
    """Parse a JSON conversation template into a ConversationTemplate object."""
    template = ConversationTemplate(
        id=data.get("id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
    )

    for node_data in data.get("nodes", []):
        template.nodes.append(_parse_node(node_data))

    for edge_data in data.get("edges", []):
        template.edges.append(_parse_edge(edge_data))

    return template


def load_conversation_template(path: Path) -> ConversationTemplate:
    """Load a conversation template from a JSON file."""
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    return parse_conversation_template(data)


def conversation_template_to_nodes_edges(
    template: ConversationTemplate,
    source_file: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert a ConversationTemplate to nodes+edges dicts for build.py.

    Returns:
        Tuple of (nodes, edges) dicts compatible with nexo's build.py
    """
    nodes = []
    edges = []

    for node in template.nodes:
        node_dict: dict[str, Any] = {
            "id": node.id,
            "label": node.label,
            "type": _get_node_type(node),
            "source_file": source_file,
            "description": node.description,
        }

        # Add type-specific fields
        if isinstance(node, IntentNode):
            node_dict["triggers"] = node.triggers
            node_dict["confidence_threshold"] = node.confidence_threshold
        elif isinstance(node, ResponseNode):
            node_dict["templates"] = node.templates
            node_dict["tone"] = node.tone
            node_dict["context"] = node.context
        elif isinstance(node, StateNode):
            node_dict["required_slots"] = node.required_slots
            node_dict["optional_slots"] = node.optional_slots
        elif isinstance(node, FailureStateNode):
            node_dict["recovery_path"] = node.recovery_path
            node_dict["max_retries"] = node.max_retries

        nodes.append(node_dict)

    for edge in template.edges:
        edge_dict: dict[str, Any] = {
            "source": edge.source,
            "target": edge.target,
            "relation": edge.relation,
            "confidence": "EXTRACTED",
        }

        if edge.condition:
            edge_dict["condition"] = edge.condition
        if edge.weight != 1.0:
            edge_dict["weight"] = edge.weight

        edges.append(edge_dict)

    return nodes, edges


def _get_node_type(node: IntentNode | ResponseNode | StateNode | FailureStateNode) -> str:
    """Get the string type name for a node."""
    if isinstance(node, IntentNode):
        return "intent"
    elif isinstance(node, ResponseNode):
        return "response"
    elif isinstance(node, FailureStateNode):
        return "failure_state"
    else:
        return "state"


def extract_conversation_templates(
    template_paths: list[Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract nodes+edges from multiple conversation template files.

    Args:
        template_paths: List of paths to JSON template files

    Returns:
        Tuple of (all_nodes, all_edges) for build.py
    """
    all_nodes = []
    all_edges = []

    for path in template_paths:
        try:
            template = load_conversation_template(path)
            nodes, edges = conversation_template_to_nodes_edges(
                template,
                source_file=str(path),
            )
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"Warning: Failed to parse {path}: {exc}", file=__import__("sys").stderr)

    return all_nodes, all_edges
