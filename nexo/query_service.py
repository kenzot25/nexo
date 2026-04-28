from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph

from nexo.security import sanitize_label

_ALLOWED_GRAPH_ROOTS = {"nexo-out", "workspace-nexo-out"}


class GraphQueryError(ValueError):
    """Base error for graph query failures."""


def _strip_diacritics(text: str) -> str:
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _default_terms(text: str) -> list[str]:
    terms = [t.lower() for t in text.split() if len(t) > 2]
    if not terms and text.strip():
        return [text.strip().lower()]
    return terms


def _validate_graph_path(graph_path: str | Path) -> Path:
    resolved = Path(graph_path).resolve()
    if resolved.suffix != ".json":
        raise GraphQueryError(f"Graph path must be a .json file, got: {graph_path!r}")
    if not resolved.exists():
        raise FileNotFoundError(f"Graph file not found: {resolved}")
    if not any(parent.name in _ALLOWED_GRAPH_ROOTS for parent in [resolved.parent, *resolved.parents]):
        allowed = ", ".join(sorted(_ALLOWED_GRAPH_ROOTS))
        raise GraphQueryError(
            f"Graph path must live inside one of: {allowed}. Got: {resolved}"
        )
    return resolved


def _load_graph(graph_path: str | Path) -> nx.Graph:
    resolved = _validate_graph_path(graph_path)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphQueryError(
            f"graph.json is corrupted ({exc}). Re-run nexo update . to rebuild."
        ) from exc
    try:
        return json_graph.node_link_graph(data, edges="links")
    except TypeError:
        return json_graph.node_link_graph(data)


def _communities_from_graph(G: nx.Graph) -> dict[int, list[str]]:
    communities: dict[int, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        cid = data.get("community")
        if cid is not None:
            communities.setdefault(int(cid), []).append(node_id)
    return communities


def _score_nodes(G: nx.Graph, terms: list[str]) -> list[tuple[float, str]]:
    scored = []
    norm_terms = [_strip_diacritics(t).lower() for t in terms]
    for nid, data in G.nodes(data=True):
        norm_label = data.get("norm_label") or _strip_diacritics(data.get("label") or "").lower()
        source = (data.get("source_file") or "").lower()
        score = sum(1 for t in norm_terms if t in norm_label) + sum(0.5 for t in norm_terms if t in source)
        if score > 0:
            scored.append((score, nid))
    return sorted(scored, reverse=True)


def _bfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple[str, str]]]:
    visited: set[str] = set(start_nodes)
    frontier = set(start_nodes)
    edges_seen: list[tuple[str, str]] = []
    for _ in range(depth):
        next_frontier: set[str] = set()
        for node in frontier:
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    edges_seen.append((node, neighbor))
        visited.update(next_frontier)
        frontier = next_frontier
    return visited, edges_seen


def _dfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple[str, str]]]:
    visited: set[str] = set()
    edges_seen: list[tuple[str, str]] = []
    stack = [(node, 0) for node in reversed(start_nodes)]
    while stack:
        node, d = stack.pop()
        if node in visited or d > depth:
            continue
        visited.add(node)
        for neighbor in G.neighbors(node):
            if neighbor not in visited:
                stack.append((neighbor, d + 1))
                edges_seen.append((node, neighbor))
    return visited, edges_seen


def _subgraph_to_text(G: nx.Graph, nodes: set[str], edges: list[tuple[str, str]], token_budget: int = 2000) -> str:
    char_budget = token_budget * 3
    lines = []
    for nid in sorted(nodes, key=lambda node_id: G.degree(node_id), reverse=True):
        data = G.nodes[nid]
        line = (
            f"NODE {sanitize_label(data.get('label', nid))} "
            f"[src={data.get('source_file', '')} loc={data.get('source_location', '')} community={data.get('community', '')}]"
        )
        lines.append(line)
    for u, v in edges:
        if u in nodes and v in nodes:
            raw = G[u][v]
            edge = next(iter(raw.values()), {}) if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)) else raw
            line = (
                f"EDGE {sanitize_label(G.nodes[u].get('label', u))} "
                f"--{edge.get('relation', '')} [{edge.get('confidence', '')}]--> "
                f"{sanitize_label(G.nodes[v].get('label', v))}"
            )
            lines.append(line)
    output = "\n".join(lines)
    if len(output) > char_budget:
        output = output[:char_budget] + f"\n... (truncated to ~{token_budget} token budget)"
    return output


def _find_node(G: nx.Graph, label: str) -> list[str]:
    term = _strip_diacritics(label).lower()
    return [
        nid
        for nid, data in G.nodes(data=True)
        if term in (data.get("norm_label") or _strip_diacritics(data.get("label") or "").lower())
        or term == nid.lower()
    ]


def _node_payload(G: nx.Graph, node_id: str, score: float | None = None, include_source: bool = True) -> dict[str, Any]:
    data = G.nodes[node_id]
    payload: dict[str, Any] = {
        "node_id": node_id,
        "label": data.get("label", node_id),
        "community": data.get("community"),
        "degree": G.degree(node_id),
    }
    if score is not None:
        payload["score"] = float(score)
    if include_source:
        payload["source_file"] = data.get("source_file", "")
        payload["source_location"] = data.get("source_location", "")
        payload["file_type"] = data.get("file_type", "")
    return payload


def resolve_nodes(
    query: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
    top_k: int = 5,
    include_source: bool = True,
) -> dict[str, Any]:
    G = _load_graph(graph_path)
    terms = _default_terms(query)
    scored = _score_nodes(G, terms)
    matches = [_node_payload(G, node_id, score=score, include_source=include_source) for score, node_id in scored[:top_k]]
    return {
        "query": query,
        "terms": terms,
        "graph_path": str(_validate_graph_path(graph_path)),
        "matches": matches,
        "match_count": len(scored),
        "text": "No matching nodes found." if not matches else "\n".join(
            f"{idx}. {item['label']} (score={item['score']:.2f}, community={item['community']})"
            for idx, item in enumerate(matches, start=1)
        ),
    }


def query_graph(
    question: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
    use_dfs: bool = False,
    budget: int = 2000,
    depth: int = 2,
    top_k: int = 5,
) -> dict[str, Any]:
    G = _load_graph(graph_path)
    terms = _default_terms(question)
    scored = _score_nodes(G, terms)
    if not scored:
        return {
            "question": question,
            "terms": terms,
            "graph_path": str(_validate_graph_path(graph_path)),
            "matches": [],
            "nodes": [],
            "edges": [],
            "text": "No matching nodes found.",
            "truncated": False,
        }
    start = [node_id for _, node_id in scored[:top_k]]
    nodes, edges = (_dfs if use_dfs else _bfs)(G, start, depth=depth)
    text = _subgraph_to_text(G, nodes, edges, token_budget=budget)
    return {
        "question": question,
        "terms": terms,
        "graph_path": str(_validate_graph_path(graph_path)),
        "matches": [_node_payload(G, node_id, score=score) for score, node_id in scored[:top_k]],
        "nodes": [_node_payload(G, node_id) for node_id in sorted(nodes)],
        "edges": [_edge_payload(G, u, v) for u, v in edges if u in nodes and v in nodes],
        "text": text,
        "truncated": "truncated" in text,
    }


def _resolve_best_match(G: nx.Graph, label_or_id: str) -> tuple[str | None, list[dict[str, Any]]]:
    direct_matches = _find_node(G, label_or_id)
    if direct_matches:
        candidates = [_node_payload(G, node_id) for node_id in direct_matches[:5]]
        return direct_matches[0], candidates
    scored = _score_nodes(G, _default_terms(label_or_id))
    candidates = [_node_payload(G, node_id, score=score) for score, node_id in scored[:5]]
    if not scored:
        return None, []
    return scored[0][1], candidates


def _edge_payload(G: nx.Graph, source: str, target: str) -> dict[str, Any]:
    raw = G[source][target]
    edge = next(iter(raw.values()), {}) if isinstance(G, (nx.MultiGraph, nx.MultiDiGraph)) else raw
    return {
        "source": source,
        "source_label": G.nodes[source].get("label", source),
        "target": target,
        "target_label": G.nodes[target].get("label", target),
        "relation": edge.get("relation", ""),
        "confidence": edge.get("confidence", ""),
    }


def shortest_path_query(
    source_label: str,
    target_label: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
) -> dict[str, Any]:
    import networkx as _nx

    G = _load_graph(graph_path)
    source_id, source_candidates = _resolve_best_match(G, source_label)
    target_id, target_candidates = _resolve_best_match(G, target_label)
    if source_id is None:
        return {
            "source_query": source_label,
            "target_query": target_label,
            "graph_path": str(_validate_graph_path(graph_path)),
            "resolved_source": None,
            "resolved_target": None,
            "segments": [],
            "hop_count": 0,
            "text": f"No node matching '{source_label}' found.",
            "source_candidates": source_candidates,
            "target_candidates": target_candidates,
        }
    if target_id is None:
        return {
            "source_query": source_label,
            "target_query": target_label,
            "graph_path": str(_validate_graph_path(graph_path)),
            "resolved_source": _node_payload(G, source_id),
            "resolved_target": None,
            "segments": [],
            "hop_count": 0,
            "text": f"No node matching '{target_label}' found.",
            "source_candidates": source_candidates,
            "target_candidates": target_candidates,
        }
    try:
        path_nodes = _nx.shortest_path(G, source_id, target_id)
    except (_nx.NetworkXNoPath, _nx.NodeNotFound):
        return {
            "source_query": source_label,
            "target_query": target_label,
            "graph_path": str(_validate_graph_path(graph_path)),
            "resolved_source": _node_payload(G, source_id),
            "resolved_target": _node_payload(G, target_id),
            "segments": [],
            "hop_count": 0,
            "text": f"No path found between '{source_label}' and '{target_label}'.",
            "source_candidates": source_candidates,
            "target_candidates": target_candidates,
        }

    segments = [_edge_payload(G, path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)]
    pieces = [G.nodes[path_nodes[0]].get("label", path_nodes[0])]
    for segment in segments:
        conf = f" [{segment['confidence']}]" if segment["confidence"] else ""
        pieces.append(f"--{segment['relation']}{conf}--> {segment['target_label']}")
    text = f"Shortest path ({len(path_nodes) - 1} hops):\n  " + " ".join(pieces)
    return {
        "source_query": source_label,
        "target_query": target_label,
        "graph_path": str(_validate_graph_path(graph_path)),
        "resolved_source": _node_payload(G, source_id),
        "resolved_target": _node_payload(G, target_id),
        "path_nodes": [_node_payload(G, node_id) for node_id in path_nodes],
        "segments": segments,
        "hop_count": len(path_nodes) - 1,
        "text": text,
        "source_candidates": source_candidates,
        "target_candidates": target_candidates,
    }


def explain_node_query(
    label: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
    neighbor_limit: int = 20,
) -> dict[str, Any]:
    G = _load_graph(graph_path)
    node_id, candidates = _resolve_best_match(G, label)
    if node_id is None:
        return {
            "query": label,
            "graph_path": str(_validate_graph_path(graph_path)),
            "resolved_node": None,
            "neighbors": [],
            "candidate_matches": candidates,
            "text": f"No node matching '{label}' found.",
        }

    data = G.nodes[node_id]
    neighbors = list(G.neighbors(node_id))
    top_neighbors = sorted(neighbors, key=lambda nb: G.degree(nb), reverse=True)[:neighbor_limit]
    relations = []
    for neighbor in top_neighbors:
        edge = _edge_payload(G, node_id, neighbor)
        relations.append({**_node_payload(G, neighbor), **edge})

    lines = [
        f"Node: {data.get('label', node_id)}",
        f"  ID:        {node_id}",
        f"  Source:    {data.get('source_file', '')} {data.get('source_location', '')}".rstrip(),
        f"  Type:      {data.get('file_type', '')}",
        f"  Community: {data.get('community', '')}",
        f"  Degree:    {G.degree(node_id)}",
    ]
    if relations:
        lines.append("")
        lines.append(f"Connections ({len(neighbors)}):")
        for rel in relations:
            lines.append(f"  --> {rel['target_label']} [{rel['relation']}] [{rel['confidence']}]")
        if len(neighbors) > neighbor_limit:
            lines.append(f"  ... and {len(neighbors) - neighbor_limit} more")

    return {
        "query": label,
        "graph_path": str(_validate_graph_path(graph_path)),
        "resolved_node": _node_payload(G, node_id),
        "candidate_matches": candidates,
        "neighbors": relations,
        "text": "\n".join(lines),
    }


def expand_subgraph(
    seeds: list[str],
    *,
    strategy: str = "bfs",
    depth: int = 2,
    token_budget: int = 2000,
    graph_path: str | Path = "nexo-out/graph.json",
) -> dict[str, Any]:
    G = _load_graph(graph_path)
    resolved: list[dict[str, Any]] = []
    node_ids: list[str] = []
    for seed in seeds:
        node_id, candidates = _resolve_best_match(G, seed)
        if node_id is not None:
            node_ids.append(node_id)
            resolved.append({"query": seed, "resolved": _node_payload(G, node_id), "candidates": candidates})
        else:
            resolved.append({"query": seed, "resolved": None, "candidates": candidates})

    if not node_ids:
        return {
            "graph_path": str(_validate_graph_path(graph_path)),
            "strategy": strategy,
            "depth": depth,
            "token_budget": token_budget,
            "resolved_seeds": resolved,
            "nodes": [],
            "edges": [],
            "text": "No matching nodes found.",
            "truncated": False,
        }

    walker = _dfs if strategy == "dfs" else _bfs
    nodes, edges = walker(G, node_ids, depth=depth)
    text = _subgraph_to_text(G, nodes, edges, token_budget=token_budget)
    return {
        "graph_path": str(_validate_graph_path(graph_path)),
        "strategy": strategy,
        "depth": depth,
        "token_budget": token_budget,
        "resolved_seeds": resolved,
        "nodes": [_node_payload(G, node_id) for node_id in sorted(nodes)],
        "edges": [_edge_payload(G, u, v) for u, v in edges if u in nodes and v in nodes],
        "text": text,
        "truncated": "truncated" in text,
    }


def graph_summary(*, graph_path: str | Path = "nexo-out/graph.json") -> dict[str, Any]:
    G = _load_graph(graph_path)
    communities = _communities_from_graph(G)
    ranked_nodes = sorted(G.nodes(), key=lambda node_id: G.degree(node_id), reverse=True)
    god_nodes = [_node_payload(G, node_id) for node_id in ranked_nodes[:10]]
    top_communities = sorted(communities.items(), key=lambda item: len(item[1]), reverse=True)[:10]
    summary = {
        "graph_path": str(_validate_graph_path(graph_path)),
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "community_count": len(communities),
        "god_nodes": god_nodes,
        "top_communities": [
            {
                "community": cid,
                "size": len(nodes),
                "sample_labels": [G.nodes[node_id].get("label", node_id) for node_id in nodes[:5]],
            }
            for cid, nodes in top_communities
        ],
        "suggested_next_calls": [
            "resolve_nodes for fuzzy entity names",
            "shortest_path for relationship questions",
            "explain_node for one concept",
            "expand_subgraph for architecture context",
        ],
    }
    summary["text"] = (
        f"Graph: {summary['node_count']} nodes, {summary['edge_count']} edges, "
        f"{summary['community_count']} communities. Top nodes: "
        + ", ".join(node["label"] for node in god_nodes[:5])
    )
    return summary


def read_graph_report(*, graph_path: str | Path = "nexo-out/graph.json") -> str:
    resolved = _validate_graph_path(graph_path)
    report_path = resolved.parent / "GRAPH_REPORT.md"
    if not report_path.exists():
        raise FileNotFoundError(f"Graph report not found: {report_path}")
    return report_path.read_text(encoding="utf-8")


# ── Conversation graph query functions ───────────────────────────────────────


def detect_ambiguity(
    user_input: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
    top_k: int = 5,
    threshold: float = 0.7,
) -> dict[str, Any]:
    """Check if user input matches multiple intents (ambiguity detection).

    Args:
        user_input: User's input text
        graph_path: Path to graph.json
        top_k: Number of top matches to return
        threshold: Minimum score to consider a match

    Returns:
        Dict with is_ambiguous flag and candidate intents
    """
    G = _load_graph(graph_path)
    terms = _default_terms(user_input)

    # Find all intent nodes
    intent_nodes = [
        (nid, data)
        for nid, data in G.nodes(data=True)
        if data.get("type") == "intent"
    ]

    # Score each intent node against the input
    matches = []
    for nid, data in intent_nodes:
        triggers = data.get("triggers", [])
        label = (data.get("label") or "").lower()

        # Check if any trigger matches
        score = sum(
            1 for t in terms
            if any(t in trigger.lower() for trigger in triggers)
        )
        # Also check label match
        if any(t in label for t in terms):
            score += 0.5

        if score >= threshold:
            matches.append({
                "node_id": nid,
                "label": data.get("label", nid),
                "score": score,
                "triggers": triggers,
            })

    # Sort by score descending
    matches.sort(key=lambda m: m["score"], reverse=True)
    matches = matches[:top_k]

    is_ambiguous = len(matches) > 1

    return {
        "user_input": user_input,
        "is_ambiguous": is_ambiguous,
        "match_count": len(matches),
        "candidates": matches,
        "text": (
            f"Ambiguous: {len(matches)} intents match" if is_ambiguous
            else f"Clear: {len(matches)} intent match" if matches
            else "No matching intents found"
        ),
    }


def get_valid_next_states(
    current_state: str,
    user_input: str | None = None,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
) -> dict[str, Any]:
    """Get valid next states from current conversation position.

    Args:
        current_state: Current state node ID or label
        user_input: Optional user input to filter transitions by condition
        graph_path: Path to graph.json

    Returns:
        Dict with valid next states and transition info
    """
    G = _load_graph(graph_path)

    # Resolve current state node
    node_ids = _find_node(G, current_state)
    if not node_ids:
        return {
            "current_state": current_state,
            "error": f"State '{current_state}' not found",
            "next_states": [],
            "text": f"State '{current_state}' not found in graph",
        }

    current_nid = node_ids[0]
    current_data = G.nodes[current_nid]

    # Find outgoing edges from current state
    next_states = []
    for neighbor in G.neighbors(current_nid):
        edge_data = G[current_nid][neighbor]
        # Get edge attributes (may be nested)
        if isinstance(G, nx.MultiGraph):
            edge_attrs = next(iter(edge_data.values()), {})
        else:
            edge_attrs = edge_data

        condition = edge_attrs.get("condition")
        relation = edge_attrs.get("relation", "leads_to")

        # Skip if condition doesn't match user input
        if user_input and condition:
            if condition.lower() not in user_input.lower():
                continue

        neighbor_data = G.nodes[neighbor]
        next_states.append({
            "node_id": neighbor,
            "label": neighbor_data.get("label", neighbor),
            "type": neighbor_data.get("type", "unknown"),
            "condition": condition,
            "relation": relation,
        })

    return {
        "current_state": current_data.get("label", current_nid),
        "next_states": next_states,
        "count": len(next_states),
        "text": (
            f"From '{current_data.get('label', current_nid)}': "
            f"{len(next_states)} valid next states"
        ),
    }


def find_conversation_paths(
    goal: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
    max_paths: int = 5,
) -> dict[str, Any]:
    """Find conversation paths to reach a goal state.

    Args:
        goal: Goal state node ID or label
        graph_path: Path to graph.json
        max_paths: Maximum number of paths to return

    Returns:
        Dict with paths from entry points to goal
    """
    import networkx as nx

    G = _load_graph(graph_path)

    # Resolve goal node
    goal_ids = _find_node(G, goal)
    if not goal_ids:
        return {
            "goal": goal,
            "error": f"Goal '{goal}' not found",
            "paths": [],
            "text": f"Goal '{goal}' not found in graph",
        }

    goal_nid = goal_ids[0]

    # Find entry points (intent nodes with no incoming edges from states)
    entry_points = [
        nid for nid, data in G.nodes(data=True)
        if data.get("type") == "intent"
    ]

    if not entry_points:
        entry_points = [nid for nid in G.nodes() if G.in_degree(nid) == 0]

    # Find shortest paths from entry points to goal
    paths = []
    for entry in entry_points[:10]:  # Limit entry points to check
        try:
            path = nx.shortest_path(G, entry, goal_nid)
            if len(path) > 1:
                path_labels = [G.nodes[nid].get("label", nid) for nid in path]
                paths.append({
                    "entry": G.nodes[entry].get("label", entry),
                    "nodes": path,
                    "labels": path_labels,
                    "length": len(path) - 1,
                })
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    paths.sort(key=lambda p: p["length"])
    paths = paths[:max_paths]

    return {
        "goal": G.nodes[goal_nid].get("label", goal_nid),
        "paths": paths,
        "path_count": len(paths),
        "text": (
            f"Found {len(paths)} paths to '{G.nodes[goal_nid].get('label', goal_nid)}'"
            if paths
            else f"No paths found to '{goal}'"
        ),
    }


def get_recovery_path(
    failure_state: str,
    *,
    graph_path: str | Path = "nexo-out/graph.json",
) -> dict[str, Any]:
    """Get recovery path for a failure state.

    Args:
        failure_state: Failure state node ID or label
        graph_path: Path to graph.json

    Returns:
        Dict with recovery path and max retries
    """
    import networkx as nx

    G = _load_graph(graph_path)

    # Resolve failure state node
    node_ids = _find_node(G, failure_state)
    if not node_ids:
        return {
            "failure_state": failure_state,
            "error": f"Failure state '{failure_state}' not found",
            "text": f"Failure state '{failure_state}' not found",
        }

    failure_nid = node_ids[0]
    failure_data = G.nodes[failure_nid]

    # Check if it's actually a failure state
    if failure_data.get("type") != "failure_state":
        return {
            "failure_state": failure_data.get("label", failure_nid),
            "warning": "Node is not a failure_state type",
            "text": f"'{failure_data.get('label', failure_nid)}' is not a failure state",
        }

    # Get recovery path from node attributes
    recovery_path = failure_data.get("recovery_path", "")
    max_retries = failure_data.get("max_retries", 2)

    # Try to resolve recovery path
    recovery_node = None
    if recovery_path:
        recovery_ids = _find_node(G, recovery_path)
        if recovery_ids:
            recovery_node = {
                "node_id": recovery_ids[0],
                "label": G.nodes[recovery_ids[0]].get("label", recovery_path),
                "type": G.nodes[recovery_ids[0]].get("type"),
            }

    # Find path to recovery node if specified
    path_to_recovery = None
    if recovery_node:
        try:
            path = nx.shortest_path(G, failure_nid, recovery_node["node_id"])
            path_labels = [G.nodes[nid].get("label", nid) for nid in path]
            path_to_recovery = {
                "nodes": path,
                "labels": path_labels,
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

    return {
        "failure_state": failure_data.get("label", failure_nid),
        "recovery_path": recovery_path,
        "max_retries": max_retries,
        "recovery_node": recovery_node,
        "path_to_recovery": path_to_recovery,
        "text": (
            f"Recovery from '{failure_data.get('label', failure_nid)}': "
            f"{recovery_path} (max {max_retries} retries)"
            if recovery_path
            else f"No recovery path defined for '{failure_data.get('label', failure_nid)}'"
        ),
    }