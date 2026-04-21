import json

import networkx as nx
from networkx.readwrite import json_graph


def _write_graph(tmp_path):
    out = tmp_path / "nexo-out"
    out.mkdir()

    graph = nx.Graph()
    graph.add_node("n1", label="AuthModule", source_file="auth.py", source_location="L10", community=0)
    graph.add_node("n2", label="Transport", source_file="transport.py", source_location="L5", community=0)
    graph.add_node("n3", label="Database", source_file="db.py", source_location="L2", community=1)
    graph.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED")
    graph.add_edge("n2", "n3", relation="uses", confidence="INFERRED")

    graph_path = out / "graph.json"
    graph_path.write_text(json.dumps(json_graph.node_link_data(graph, edges="links")), encoding="utf-8")
    (out / "GRAPH_REPORT.md").write_text("# Report\n", encoding="utf-8")
    return graph_path


def test_resolve_nodes_returns_scored_matches(tmp_path):
    from nexo.query_service import resolve_nodes

    graph_path = _write_graph(tmp_path)
    result = resolve_nodes("auth", graph_path=graph_path)

    assert result["match_count"] == 1
    assert result["matches"][0]["label"] == "AuthModule"


def test_shortest_path_query_returns_segments(tmp_path):
    from nexo.query_service import shortest_path_query

    graph_path = _write_graph(tmp_path)
    result = shortest_path_query("AuthModule", "Database", graph_path=graph_path)

    assert result["hop_count"] == 2
    assert len(result["segments"]) == 2
    assert "Shortest path" in result["text"]


def test_explain_node_query_returns_neighbors(tmp_path):
    from nexo.query_service import explain_node_query

    graph_path = _write_graph(tmp_path)
    result = explain_node_query("Transport", graph_path=graph_path)

    assert result["resolved_node"]["label"] == "Transport"
    assert len(result["neighbors"]) == 2
    assert "Connections" in result["text"]


def test_expand_subgraph_uses_bfs(tmp_path):
    from nexo.query_service import expand_subgraph

    graph_path = _write_graph(tmp_path)
    result = expand_subgraph(["AuthModule"], graph_path=graph_path, depth=2)

    assert len(result["nodes"]) == 3
    assert len(result["edges"]) == 2


def test_graph_summary_reads_graph(tmp_path):
    from nexo.query_service import graph_summary, read_graph_report

    graph_path = _write_graph(tmp_path)
    summary = graph_summary(graph_path=graph_path)

    assert summary["node_count"] == 3
    assert summary["community_count"] == 2
    assert read_graph_report(graph_path=graph_path).startswith("# Report")