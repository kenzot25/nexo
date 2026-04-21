# write graph to HTML, JSON, SVG, GraphML, Obsidian vault, and Neo4j Cypher
from __future__ import annotations
import html as _html
import json
import math
import re
from collections import Counter
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph
from nexo.security import sanitize_label
from nexo.analyze import _node_community_map

def _strip_diacritics(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


COMMUNITY_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
]

MAX_NODES_FOR_VIZ = 5_000


def _html_styles() -> str:
    return """<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f1a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; display: flex; height: 100vh; overflow: hidden; }
  #graph { flex: 1; }
  #sidebar { width: 280px; background: #1a1a2e; border-left: 1px solid #2a2a4e; display: flex; flex-direction: column; overflow: hidden; }
  #search-wrap { padding: 12px; border-bottom: 1px solid #2a2a4e; }
  #search { width: 100%; background: #0f0f1a; border: 1px solid #3a3a5e; color: #e0e0e0; padding: 7px 10px; border-radius: 6px; font-size: 13px; outline: none; }
  #search:focus { border-color: #4E79A7; }
  #search-results { max-height: 140px; overflow-y: auto; padding: 4px 12px; border-bottom: 1px solid #2a2a4e; display: none; }
  .search-item { padding: 4px 6px; cursor: pointer; border-radius: 4px; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .search-item:hover { background: #2a2a4e; }
  #info-panel { padding: 14px; border-bottom: 1px solid #2a2a4e; min-height: 140px; }
  #info-panel h3 { font-size: 13px; color: #aaa; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
  #info-content { font-size: 13px; color: #ccc; line-height: 1.6; }
  #info-content .field { margin-bottom: 5px; }
  #info-content .field b { color: #e0e0e0; }
  #info-content .empty { color: #555; font-style: italic; }
  .neighbor-link { display: block; padding: 2px 6px; margin: 2px 0; border-radius: 3px; cursor: pointer; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-left: 3px solid #333; }
  .neighbor-link:hover { background: #2a2a4e; }
  #neighbors-list { max-height: 160px; overflow-y: auto; margin-top: 4px; }
  #legend-wrap { flex: 1; overflow-y: auto; padding: 12px; }
  #legend-wrap h3 { font-size: 13px; color: #aaa; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
  .legend-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer; border-radius: 4px; font-size: 12px; }
  .legend-item:hover { background: #2a2a4e; padding-left: 4px; }
  .legend-item.dimmed { opacity: 0.35; }
  .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .legend-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .legend-count { color: #666; font-size: 11px; }
  #stats { padding: 10px 14px; border-top: 1px solid #2a2a4e; font-size: 11px; color: #555; }
</style>"""


def _hyperedge_script(hyperedges_json: str) -> str:
    return f"""<script>
// Render hyperedges as shaded regions
const hyperedges = {hyperedges_json};
// afterDrawing passes ctx already transformed to network coordinate space.
// Draw node positions raw — no manual pan/zoom/DPR math needed.
network.on('afterDrawing', function(ctx) {{
    hyperedges.forEach(h => {{
        const positions = h.nodes
            .map(nid => network.getPositions([nid])[nid])
            .filter(p => p !== undefined);
        if (positions.length < 2) return;
        ctx.save();
        ctx.globalAlpha = 0.12;
        ctx.fillStyle = '#6366f1';
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2;
        ctx.beginPath();
        // Centroid and expanded hull in network coordinates
        const cx = positions.reduce((s, p) => s + p.x, 0) / positions.length;
        const cy = positions.reduce((s, p) => s + p.y, 0) / positions.length;
        const expanded = positions.map(p => ({{
            x: cx + (p.x - cx) * 1.15,
            y: cy + (p.y - cy) * 1.15
        }}));
        ctx.moveTo(expanded[0].x, expanded[0].y);
        expanded.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 0.4;
        ctx.stroke();
        // Label
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = '#4f46e5';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(h.label, cx, cy - 5);
        ctx.restore();
    }});
}});
</script>"""


def _html_script(nodes_json: str, edges_json: str, legend_json: str) -> str:
    return f"""<script>
const RAW_NODES = {nodes_json};
const RAW_EDGES = {edges_json};
const LEGEND = {legend_json};

// HTML-escape helper — prevents XSS when injecting graph data into innerHTML
function esc(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}}

// Build vis datasets
const nodesDS = new vis.DataSet(RAW_NODES.map(n => ({{
  id: n.id, label: n.label, color: n.color, size: n.size,
  font: n.font, title: n.title,
  _community: n.community, _community_name: n.community_name,
  _source_file: n.source_file, _file_type: n.file_type, _degree: n.degree,
}})));

const edgesDS = new vis.DataSet(RAW_EDGES.map((e, i) => ({{
  id: i, from: e.from, to: e.to,
  label: '',
  title: e.title,
  dashes: e.dashes,
  width: e.width,
  color: e.color,
  arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
}})));

const container = document.getElementById('graph');
const network = new vis.Network(container, {{ nodes: nodesDS, edges: edgesDS }}, {{
  physics: {{
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{
      gravitationalConstant: -60,
      centralGravity: 0.005,
      springLength: 120,
      springConstant: 0.08,
      damping: 0.4,
      avoidOverlap: 0.8,
    }},
    stabilization: {{ iterations: 200, fit: true }},
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 100,
    hideEdgesOnDrag: true,
    navigationButtons: false,
    keyboard: false,
  }},
  nodes: {{ shape: 'dot', borderWidth: 1.5 }},
  edges: {{ smooth: {{ type: 'continuous', roundness: 0.2 }}, selectionWidth: 3 }},
}});

network.once('stabilizationIterationsDone', () => {{
  network.setOptions({{ physics: {{ enabled: false }} }});
}});

function showInfo(nodeId) {{
  const n = nodesDS.get(nodeId);
  if (!n) return;
  const neighborIds = network.getConnectedNodes(nodeId);
  const neighborItems = neighborIds.map(nid => {{
    const nb = nodesDS.get(nid);
    const color = nb ? nb.color.background : '#555';
    return `<span class="neighbor-link" style="border-left-color:${{esc(color)}}" onclick="focusNode(${{JSON.stringify(nid)}})">${{esc(nb ? nb.label : nid)}}</span>`;
  }}).join('');
  document.getElementById('info-content').innerHTML = `
    <div class="field"><b>${{esc(n.label)}}</b></div>
    <div class="field">Type: ${{esc(n._file_type || 'unknown')}}</div>
    <div class="field">Community: ${{esc(n._community_name)}}</div>
    <div class="field">Source: ${{esc(n._source_file || '-')}}</div>
    <div class="field">Degree: ${{n._degree}}</div>
    ${{neighborIds.length ? `<div class="field" style="margin-top:8px;color:#aaa;font-size:11px">Neighbors (${{neighborIds.length}})</div><div id="neighbors-list">${{neighborItems}}</div>` : ''}}
  `;
}}

function focusNode(nodeId) {{
  network.focus(nodeId, {{ scale: 1.4, animation: true }});
  network.selectNodes([nodeId]);
  showInfo(nodeId);
}}

// Track hovered node — hover detection is more reliable than click params
let hoveredNodeId = null;
network.on('hoverNode', params => {{
  hoveredNodeId = params.node;
  container.style.cursor = 'pointer';
}});
network.on('blurNode', () => {{
  hoveredNodeId = null;
  container.style.cursor = 'default';
}});
container.addEventListener('click', () => {{
  if (hoveredNodeId !== null) {{
    showInfo(hoveredNodeId);
    network.selectNodes([hoveredNodeId]);
  }}
}});
network.on('click', params => {{
  if (params.nodes.length > 0) {{
    showInfo(params.nodes[0]);
  }} else if (hoveredNodeId === null) {{
    document.getElementById('info-content').innerHTML = '<span class="empty">Click a node to inspect it</span>';
  }}
}});

const searchInput = document.getElementById('search');
const searchResults = document.getElementById('search-results');
searchInput.addEventListener('input', () => {{
  const q = searchInput.value.toLowerCase().trim();
  searchResults.innerHTML = '';
  if (!q) {{ searchResults.style.display = 'none'; return; }}
  const matches = RAW_NODES.filter(n => n.label.toLowerCase().includes(q)).slice(0, 20);
  if (!matches.length) {{ searchResults.style.display = 'none'; return; }}
  searchResults.style.display = 'block';
  matches.forEach(n => {{
    const el = document.createElement('div');
    el.className = 'search-item';
    el.textContent = n.label;
    el.style.borderLeft = `3px solid ${{n.color.background}}`;
    el.style.paddingLeft = '8px';
    el.onclick = () => {{
      network.focus(n.id, {{ scale: 1.5, animation: true }});
      network.selectNodes([n.id]);
      showInfo(n.id);
      searchResults.style.display = 'none';
      searchInput.value = '';
    }};
    searchResults.appendChild(el);
  }});
}});
document.addEventListener('click', e => {{
  if (!searchResults.contains(e.target) && e.target !== searchInput)
    searchResults.style.display = 'none';
}});

const hiddenCommunities = new Set();
const legendEl = document.getElementById('legend');
LEGEND.forEach(c => {{
  const item = document.createElement('div');
  item.className = 'legend-item';
  item.innerHTML = `<div class="legend-dot" style="background:${{c.color}}"></div>
    <span class="legend-label">${{c.label}}</span>
    <span class="legend-count">${{c.count}}</span>`;
  item.onclick = () => {{
    if (hiddenCommunities.has(c.cid)) {{
      hiddenCommunities.delete(c.cid);
      item.classList.remove('dimmed');
    }} else {{
      hiddenCommunities.add(c.cid);
      item.classList.add('dimmed');
    }}
    const updates = RAW_NODES
      .filter(n => n.community === c.cid)
      .map(n => ({{ id: n.id, hidden: hiddenCommunities.has(c.cid) }}));
    nodesDS.update(updates);
  }};
  legendEl.appendChild(item);
}});
</script>"""


_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}


def attach_hyperedges(G: nx.Graph, hyperedges: list) -> None:
    """Store hyperedges in the graph's metadata dict."""
    existing = G.graph.get("hyperedges", [])
    seen_ids = {h["id"] for h in existing}
    for h in hyperedges:
        if h.get("id") and h["id"] not in seen_ids:
            existing.append(h)
            seen_ids.add(h["id"])
    G.graph["hyperedges"] = existing


def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str) -> None:
    node_community = _node_community_map(communities)
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)
    for node in data["nodes"]:
        node["community"] = node_community.get(node["id"])
        node["norm_label"] = _strip_diacritics(node.get("label", "")).lower()
    for link in data["links"]:
        if "confidence_score" not in link:
            conf = link.get("confidence", "EXTRACTED")
            link["confidence_score"] = _CONFIDENCE_SCORE_DEFAULTS.get(conf, 1.0)
    data["hyperedges"] = getattr(G, "graph", {}).get("hyperedges", [])
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def to_cypher(G: nx.Graph, output_path: str) -> None:
    """Export graph as Neo4j Cypher MERGE statements."""

    def _esc(value: object) -> str:
        return str(value).replace("\\", "\\\\").replace("'", "\\'")

    def _rel_type(raw: object) -> str:
        text = re.sub(r"[^A-Za-z0-9_]", "_", str(raw or "RELATED_TO").upper())
        if not text or text[0].isdigit():
            return f"R_{text}" if text else "RELATED_TO"
        return text

    lines: list[str] = []
    for node_id, data in G.nodes(data=True):
        nid = _esc(node_id)
        label = _esc(data.get("label", node_id))
        source = _esc(data.get("source_file", ""))
        lines.append(
            f"MERGE (n:Entity {{id: '{nid}'}}) "
            f"SET n.label = '{label}', n.source_file = '{source}';"
        )

    for u, v, data in G.edges(data=True):
        src = _esc(u)
        dst = _esc(v)
        rel = _rel_type(data.get("relation"))
        conf = _esc(data.get("confidence", "EXTRACTED"))
        lines.append(
            f"MATCH (a:Entity {{id: '{src}'}}), (b:Entity {{id: '{dst}'}}) "
            f"MERGE (a)-[r:{rel}]->(b) "
            f"SET r.confidence = '{conf}';"
        )

    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def to_graphml(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
 ) -> None:
    """Export graph to GraphML with a community attribute on each node."""
    node_community = _node_community_map(communities)
    out = nx.Graph()

    for node_id, data in G.nodes(data=True):
        attrs = dict(data)
        attrs["community"] = node_community.get(node_id)
        out.add_node(node_id, **attrs)

    for u, v, data in G.edges(data=True):
        out.add_edge(u, v, **dict(data))

    nx.write_graphml(out, output_path)


def prune_dangling_edges(graph_data: dict) -> tuple[dict, int]:
    """Remove edges whose source or target node is not in the node set.

    Returns the cleaned graph_data dict and the number of pruned edges.
    """
    node_ids = {n["id"] for n in graph_data["nodes"]}
    links_key = "links" if "links" in graph_data else "edges"
    before = len(graph_data[links_key])
    graph_data[links_key] = [
        e for e in graph_data[links_key]
        if e["source"] in node_ids and e["target"] in node_ids
    ]
    return graph_data, before - len(graph_data[links_key])



def to_html(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
    community_labels: dict[int, str] | None = None,
) -> None:
    """Generate an interactive vis.js HTML visualization of the graph.

    Features: node size by degree, click-to-inspect panel, search box,
    community filter, physics clustering by community, confidence-styled edges.
    Raises ValueError if graph exceeds MAX_NODES_FOR_VIZ.
    """
    if G.number_of_nodes() > MAX_NODES_FOR_VIZ:
        raise ValueError(
            f"Graph has {G.number_of_nodes()} nodes - too large for HTML viz. "
            f"Use --no-viz or reduce input size."
        )

    node_community = _node_community_map(communities)
    degree = dict(G.degree())
    max_deg = max(degree.values(), default=1) or 1

    # Build nodes list for vis.js
    vis_nodes = []
    for node_id, data in G.nodes(data=True):
        cid = node_community.get(node_id, 0)
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        label = sanitize_label(data.get("label", node_id))
        deg = degree.get(node_id, 1)
        size = 10 + 30 * (deg / max_deg)
        # Only show label for high-degree nodes by default; others show on hover
        font_size = 12 if deg >= max_deg * 0.15 else 0
        vis_nodes.append({
            "id": node_id,
            "label": label,
            "color": {"background": color, "border": color, "highlight": {"background": "#ffffff", "border": color}},
            "size": round(size, 1),
            "font": {"size": font_size, "color": "#ffffff"},
            "title": _html.escape(label),
            "community": cid,
            "community_name": sanitize_label((community_labels or {}).get(cid, f"Community {cid}")),
            "source_file": sanitize_label(data.get("source_file", "")),
            "file_type": data.get("file_type", ""),
            "degree": deg,
        })

    # Build edges list
    vis_edges = []
    for u, v, data in G.edges(data=True):
        confidence = data.get("confidence", "EXTRACTED")
        relation = data.get("relation", "")
        vis_edges.append({
            "from": u,
            "to": v,
            "label": relation,
            "title": _html.escape(f"{relation} [{confidence}]"),
            "dashes": confidence != "EXTRACTED",
            "width": 2 if confidence == "EXTRACTED" else 1,
            "color": {"opacity": 0.7 if confidence == "EXTRACTED" else 0.35},
            "confidence": confidence,
        })

    # Build community legend data
    legend_data = []
    for cid in sorted((community_labels or {}).keys()):
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        lbl = _html.escape(sanitize_label((community_labels or {}).get(cid, f"Community {cid}")))
        n = len(communities.get(cid, []))
        legend_data.append({"cid": cid, "color": color, "label": lbl, "count": n})

    # Escape </script> sequences so embedded JSON cannot break out of the script tag
    def _js_safe(obj) -> str:
        return json.dumps(obj).replace("</", "<\\/")

    nodes_json = _js_safe(vis_nodes)
    edges_json = _js_safe(vis_edges)
    legend_json = _js_safe(legend_data)
    hyperedges_json = _js_safe(getattr(G, "graph", {}).get("hyperedges", []))
    title = _html.escape(sanitize_label(str(output_path)))
    stats = f"{G.number_of_nodes()} nodes &middot; {G.number_of_edges()} edges &middot; {len(communities)} communities"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>nexo - {title}</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
{_html_styles()}
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search nodes..." autocomplete="off">
    <div id="search-results"></div>
  </div>
  <div id="info-panel">
    <h3>Node Info</h3>
    <div id="info-content"><span class="empty">Click a node to inspect it</span></div>
  </div>
  <div id="legend-wrap">
    <h3>Communities</h3>
    <div id="legend"></div>
  </div>
  <div id="stats">{stats}</div>
</div>
{_html_script(nodes_json, edges_json, legend_json)}
{_hyperedge_script(hyperedges_json)}
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")


# Keep backward-compatible alias - skill.md calls generate_html
generate_html = to_html


def to_obsidian(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
) -> int:
    """Export graph as an Obsidian vault - one .md file per node with [[wikilinks]],
    plus one _COMMUNITY_name.md overview note per community (sorted to top by underscore prefix).

    Open the output directory as a vault in Obsidian to get an interactive
    graph view with community colors and full-text search over node metadata.

    Returns the number of node notes + community notes written.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    node_community = _node_community_map(communities)

    # Map node_id → safe filename so wikilinks stay consistent.
    # Deduplicate: if two nodes produce the same filename, append a numeric suffix.
    def safe_name(label: str) -> str:
        cleaned = re.sub(r'[\\/*?:"<>|#^[\]]', "", label.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")).strip()
        # Strip trailing .md/.mdx/.markdown so "CLAUDE.md" doesn't become "CLAUDE.md.md"
        cleaned = re.sub(r"\.(md|mdx|markdown)$", "", cleaned, flags=re.IGNORECASE)
        return cleaned or "unnamed"

    node_filename: dict[str, str] = {}
    seen_names: dict[str, int] = {}
    for node_id, data in G.nodes(data=True):
        base = safe_name(data.get("label", node_id))
        if base in seen_names:
            seen_names[base] += 1
            node_filename[node_id] = f"{base}_{seen_names[base]}"
        else:
            seen_names[base] = 0
            node_filename[node_id] = base

    # Helper: compute dominant confidence for a node across all its edges
    def _dominant_confidence(node_id: str) -> str:
        confs = []
        for u, v, edata in G.edges(node_id, data=True):
            confs.append(edata.get("confidence", "EXTRACTED"))
        if not confs:
            return "EXTRACTED"
        return Counter(confs).most_common(1)[0][0]

    # Map file_type → nexo tag
    _FTYPE_TAG = {
        "code": "nexo/code",
        "document": "nexo/document",
        "paper": "nexo/paper",
        "image": "nexo/image",
    }

    # Write one .md file per node
    for node_id, data in G.nodes(data=True):
        label = data.get("label", node_id)
        cid = node_community.get(node_id)
        community_name = (
            community_labels.get(cid, f"Community {cid}")
            if community_labels and cid is not None
            else f"Community {cid}"
        )

        # Build tags for this node
        ftype = data.get("file_type", "")
        ftype_tag = _FTYPE_TAG.get(ftype, f"nexo/{ftype}" if ftype else "nexo/document")
        dom_conf = _dominant_confidence(node_id)
        conf_tag = f"nexo/{dom_conf}"
        comm_tag = f"community/{community_name.replace(' ', '_')}"
        node_tags = [ftype_tag, conf_tag, comm_tag]

        lines: list[str] = []

        # YAML frontmatter - readable in Obsidian's properties panel
        lines += [
            "---",
            f'source_file: "{data.get("source_file", "")}"',
            f'type: "{ftype}"',
            f'community: "{community_name}"',
        ]
        if data.get("source_location"):
            lines.append(f'location: "{data["source_location"]}"')
        # Add tags list to frontmatter
        lines.append("tags:")
        for tag in node_tags:
            lines.append(f"  - {tag}")
        lines += ["---", "", f"# {label}", ""]

        # Outgoing edges as wikilinks
        neighbors = list(G.neighbors(node_id))
        if neighbors:
            lines.append("## Connections")
            for neighbor in sorted(neighbors, key=lambda n: G.nodes[n].get("label", n)):
                edge_data = G.edges[node_id, neighbor]
                neighbor_label = node_filename[neighbor]
                relation = edge_data.get("relation", "")
                confidence = edge_data.get("confidence", "EXTRACTED")
                lines.append(f"- [[{neighbor_label}]] - `{relation}` [{confidence}]")
            lines.append("")

        # Inline tags at bottom of note body (for Obsidian tag panel)
        inline_tags = " ".join(f"#{t}" for t in node_tags)
        lines.append(inline_tags)

        fname = node_filename[node_id] + ".md"
        (out / fname).write_text("\n".join(lines), encoding="utf-8")

    # Write one _COMMUNITY_name.md overview note per community
    # Build inter-community edge counts for "Connections to other communities"
    inter_community_edges: dict[int, dict[int, int]] = {}
    for cid in communities:
        inter_community_edges[cid] = {}
    for u, v in G.edges():
        cu = node_community.get(u)
        cv = node_community.get(v)
        if cu is not None and cv is not None and cu != cv:
            inter_community_edges.setdefault(cu, {})
            inter_community_edges.setdefault(cv, {})
            inter_community_edges[cu][cv] = inter_community_edges[cu].get(cv, 0) + 1
            inter_community_edges[cv][cu] = inter_community_edges[cv].get(cu, 0) + 1

    # Precompute per-node community reach (number of distinct communities a node connects to)
    def _community_reach(node_id: str) -> int:
        neighbor_cids = {
            node_community[nb]
            for nb in G.neighbors(node_id)
            if nb in node_community and node_community[nb] != node_community.get(node_id)
        }
        return len(neighbor_cids)

    community_notes_written = 0
    for cid, members in communities.items():
        community_name = (
            community_labels.get(cid, f"Community {cid}")
            if community_labels and cid is not None
            else f"Community {cid}"
        )
        n_members = len(members)
        coh_value = cohesion.get(cid) if cohesion else None

        lines: list[str] = []

        # YAML frontmatter
        lines.append("---")
        lines.append("type: community")
        if coh_value is not None:
            lines.append(f"cohesion: {coh_value:.2f}")
        lines.append(f"members: {n_members}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {community_name}")
        lines.append("")

        # Cohesion + member count summary
        if coh_value is not None:
            cohesion_desc = (
                "tightly connected" if coh_value >= 0.7
                else "moderately connected" if coh_value >= 0.4
                else "loosely connected"
            )
            lines.append(f"**Cohesion:** {coh_value:.2f} - {cohesion_desc}")
        lines.append(f"**Members:** {n_members} nodes")
        lines.append("")

        # Members section
        lines.append("## Members")
        for node_id in sorted(members, key=lambda n: G.nodes[n].get("label", n)):
            data = G.nodes[node_id]
            node_label = node_filename[node_id]
            ftype = data.get("file_type", "")
            source = data.get("source_file", "")
            entry = f"- [[{node_label}]]"
            if ftype:
                entry += f" - {ftype}"
            if source:
                entry += f" - {source}"
            lines.append(entry)
        lines.append("")

        # Dataview live query (improvement 2)
        comm_tag_name = community_name.replace(" ", "_")
        lines.append("## Live Query (requires Dataview plugin)")
        lines.append("")
        lines.append("```dataview")
        lines.append(f"TABLE source_file, type FROM #community/{comm_tag_name}")
        lines.append("SORT file.name ASC")
        lines.append("```")
        lines.append("")

        # Connections to other communities
        cross = inter_community_edges.get(cid, {})
        if cross:
            lines.append("## Connections to other communities")
            for other_cid, edge_count in sorted(cross.items(), key=lambda x: -x[1]):
                other_name = (
                    community_labels.get(other_cid, f"Community {other_cid}")
                    if community_labels and other_cid is not None
                    else f"Community {other_cid}"
                )
                other_safe = safe_name(other_name)
                lines.append(f"- {edge_count} edge{'s' if edge_count != 1 else ''} to [[_COMMUNITY_{other_safe}]]")
            lines.append("")

        # Top bridge nodes - highest degree nodes that connect to other communities
        bridge_nodes = [
            (node_id, G.degree(node_id), _community_reach(node_id))
            for node_id in members
            if _community_reach(node_id) > 0
        ]
        bridge_nodes.sort(key=lambda x: (-x[2], -x[1]))
        top_bridges = bridge_nodes[:5]
        if top_bridges:
            lines.append("## Top bridge nodes")
            for node_id, degree, reach in top_bridges:
                node_label = node_filename[node_id]
                lines.append(
                    f"- [[{node_label}]] - degree {degree}, connects to {reach} "
                    f"{'community' if reach == 1 else 'communities'}"
                )

        community_safe = safe_name(community_name)
        fname = f"_COMMUNITY_{community_safe}.md"
        (out / fname).write_text("\n".join(lines), encoding="utf-8")
        community_notes_written += 1

    # Improvement 4: write .obsidian/graph.json to color nodes by community in graph view
    obsidian_dir = out / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)
    graph_config = {
        "colorGroups": [
            {
                "query": f"tag:#community/{label.replace(' ', '_')}",
                "color": {"a": 1, "rgb": int(COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)].lstrip('#'), 16)}
            }
            for cid, label in sorted((community_labels or {}).items())
        ]
    }
    (obsidian_dir / "graph.json").write_text(json.dumps(graph_config, indent=2), encoding="utf-8")

    return G.number_of_nodes() + community_notes_written

