"""Wikipedia-style markdown export for graph communities and key nodes."""
from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from nexo.analyze import _node_community_map


_MAX_MEMBERS_IN_ARTICLE = 25


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9 _-]", "", str(name)).strip().replace(" ", "_")
    return safe or "untitled"


def _label_for_community(cid: int, community_labels: dict[int, str] | None) -> str:
    if community_labels and cid in community_labels:
        return community_labels[cid]
    return f"Community {cid}"


def _index_md(
    communities: dict[int, list[str]],
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    god_nodes_data: list[dict] | None = None,
) -> str:
    lines = ["# index", "", "## Communities", ""]
    for cid in sorted(communities):
        label = _label_for_community(cid, community_labels)
        nodes = len(communities.get(cid, []))
        if cohesion and cid in cohesion:
            lines.append(f"- [[{label}]] - {nodes} nodes (cohesion {cohesion[cid]:.2f})")
        else:
            lines.append(f"- [[{label}]] - {nodes} nodes")

    if god_nodes_data:
        lines.extend(["", "## God Nodes", ""])
        for item in god_nodes_data:
            label = item.get("label", item.get("id", "unknown"))
            edges = int(item.get("edges", 0))
            lines.append(f"- [[{label}]] - {edges} connections")

    lines.append("")
    return "\n".join(lines)


def _community_article(
    G: nx.Graph,
    cid: int,
    members: list[str],
    node_community: dict[str, int],
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
) -> str:
    label = _label_for_community(cid, community_labels)
    lines = [f"# {label}", ""]

    if cohesion and cid in cohesion:
        lines.append(f"This community has cohesion {cohesion[cid]:.2f}.")
    lines.append(f"This article covers {len(members)} nodes.")
    lines.extend(["", "## Members", ""])

    member_labels = []
    for node_id in members:
        node_label = G.nodes[node_id].get("label", node_id)
        member_labels.append(node_label)

    for node_label in sorted(member_labels)[:_MAX_MEMBERS_IN_ARTICLE]:
        lines.append(f"- [[{node_label}]]")

    if len(member_labels) > _MAX_MEMBERS_IN_ARTICLE:
        remainder = len(member_labels) - _MAX_MEMBERS_IN_ARTICLE
        lines.append(f"- ... and {remainder} more nodes")

    # Cross-community links.
    cross: dict[int, int] = {}
    for u, v in G.edges():
        cu = node_community.get(u)
        cv = node_community.get(v)
        if cu is None or cv is None or cu == cv:
            continue
        if cu == cid:
            cross[cv] = cross.get(cv, 0) + 1
        elif cv == cid:
            cross[cu] = cross.get(cu, 0) + 1

    if cross:
        lines.extend(["", "## Cross-community Links", ""])
        for other_cid, edge_count in sorted(cross.items(), key=lambda item: (-item[1], item[0])):
            other_label = _label_for_community(other_cid, community_labels)
            lines.append(f"- [[{other_label}]] - {edge_count} edges")

    # Lightweight audit trail from touching edges.
    lines.extend(["", "## Audit Trail", ""])
    touched: set[tuple[str, str, str]] = set()
    for node_id in members:
        for neighbor in G.neighbors(node_id):
            edge = G.edges[node_id, neighbor]
            relation = edge.get("relation", "related_to")
            confidence = edge.get("confidence", "EXTRACTED")
            left = G.nodes[node_id].get("label", node_id)
            right = G.nodes[neighbor].get("label", neighbor)
            signature = tuple(sorted((left, right)) + [confidence])
            if signature in touched:
                continue
            touched.add(signature)
            lines.append(f"- {left} - {relation} - {right} [{confidence}]")

    lines.extend(["", "---", "[[index]]", ""])
    return "\n".join(lines)


def _god_node_article(
    G: nx.Graph,
    node_id: str,
    node_community: dict[str, int],
    community_labels: dict[int, str] | None = None,
) -> str:
    node = G.nodes[node_id]
    label = node.get("label", node_id)
    lines = [f"# {label}", ""]

    cid = node_community.get(node_id)
    if cid is not None:
        lines.append(f"Belongs to [[{_label_for_community(cid, community_labels)}]].")
        lines.append("")

    lines.extend(["## Connections", ""])
    neighbors = sorted(G.neighbors(node_id), key=lambda n: G.nodes[n].get("label", n))
    for neighbor in neighbors:
        edge = G.edges[node_id, neighbor]
        relation = edge.get("relation", "related_to")
        confidence = edge.get("confidence", "EXTRACTED")
        neighbor_label = G.nodes[neighbor].get("label", neighbor)
        lines.append(f"- [[{neighbor_label}]] - {relation} [{confidence}]")

    lines.extend(["", "---", "[[index]]", ""])
    return "\n".join(lines)


def to_wiki(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str | Path,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    god_nodes_data: list[dict] | None = None,
) -> int:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    node_community = _node_community_map(communities)
    created = 0

    for cid in sorted(communities):
        label = _label_for_community(cid, community_labels)
        article = _community_article(
            G,
            cid,
            communities[cid],
            node_community,
            community_labels=community_labels,
            cohesion=cohesion,
        )
        (out / f"{_safe_filename(label)}.md").write_text(article, encoding="utf-8")
        created += 1

    valid_gods: list[dict] = []
    for entry in god_nodes_data or []:
        node_id = entry.get("id")
        if not node_id or node_id not in G:
            continue
        valid_gods.append(entry)
        god_article = _god_node_article(
            G,
            node_id,
            node_community,
            community_labels=community_labels,
        )
        god_label = G.nodes[node_id].get("label", node_id)
        (out / f"{_safe_filename(god_label)}.md").write_text(god_article, encoding="utf-8")
        created += 1

    index = _index_md(
        communities,
        community_labels=community_labels,
        cohesion=cohesion,
        god_nodes_data=valid_gods,
    )
    (out / "index.md").write_text(index, encoding="utf-8")

    return created
