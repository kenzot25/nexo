import json


def test_run_workspace_query_merges_repos(monkeypatch, tmp_path):
    from nexo.workspace import run_workspace_query

    graph1 = tmp_path / "repo-a" / "nexo-out"
    graph1.mkdir(parents=True)
    (tmp_path / "repo-a" / ".git").mkdir(parents=True)
    (graph1 / "graph.json").write_text("{}", encoding="utf-8")

    graph2 = tmp_path / "repo-b" / "nexo-out"
    graph2.mkdir(parents=True)
    (tmp_path / "repo-b" / ".git").mkdir(parents=True)
    (graph2 / "graph.json").write_text("{}", encoding="utf-8")

    class FakeGraph:
        def __init__(self, label):
            self._label = label
            self.nodes = {"n1": {"label": label}}

    def fake_load_graph(path):
        return FakeGraph("NodeA" if "repo-a" in path else "NodeB")

    def fake_score_nodes(graph, terms):
        return [(2.0, "n1")]

    def fake_bfs(graph, start_nodes, depth):
        return {"n1"}, []

    def fake_to_text(graph, nodes, edges, token_budget=2000):
        return "NODE preview"

    monkeypatch.setattr("nexo.serve._load_graph", fake_load_graph)
    monkeypatch.setattr("nexo.serve._score_nodes", fake_score_nodes)
    monkeypatch.setattr("nexo.serve._bfs", fake_bfs)
    monkeypatch.setattr("nexo.serve._subgraph_to_text", fake_to_text)

    result = run_workspace_query(tmp_path, question="auth")

    assert result["repos_queried"] == 2
    assert len(result["merged_hits"]) == 2
    assert "Top merged matches:" in result["text"]


def test_run_workspace_query_uses_central_index(monkeypatch, tmp_path):
    from nexo.workspace import run_workspace_query

    out = tmp_path / "workspace-nexo-out"
    repo_out = out / "repos" / "repo-a"
    repo_out.mkdir(parents=True)
    graph_path = repo_out / "graph.json"
    graph_path.write_text("{}", encoding="utf-8")

    index = {
        "repos": [
            {
                "repo": str(tmp_path / "repo-a"),
                "repo_relative": "repo-a",
                "output": str(repo_out),
                "graph": str(graph_path),
                "ok": True,
            }
        ]
    }
    (out / "index.json").write_text(json.dumps(index), encoding="utf-8")

    class FakeGraph:
        nodes = {"n1": {"label": "NodeA"}}

    monkeypatch.setattr("nexo.serve._load_graph", lambda _: FakeGraph())
    monkeypatch.setattr("nexo.serve._score_nodes", lambda g, t: [(1.0, "n1")])
    monkeypatch.setattr("nexo.serve._bfs", lambda g, s, depth: ({"n1"}, []))
    monkeypatch.setattr("nexo.serve._subgraph_to_text", lambda g, n, e, token_budget=2000: "NODE")

    result = run_workspace_query(tmp_path, question="node", mode="central")

    assert result["repos_queried"] == 1
    assert result["repos"][0]["repo"] == "repo-a"
