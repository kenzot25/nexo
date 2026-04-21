"""CLI tests for workspace query command option parsing."""


def test_workspace_query_forwards_options(monkeypatch, tmp_path):
    from nexo import __main__ as cli

    captured = {}

    def fake_run_workspace_query(
        workspace_path,
        *,
        question,
        use_dfs=False,
        budget=2000,
        mode="auto",
        top_k=15,
    ):
        captured["workspace_path"] = workspace_path
        captured["question"] = question
        captured["use_dfs"] = use_dfs
        captured["budget"] = budget
        captured["mode"] = mode
        captured["top_k"] = top_k
        return {"text": "ok"}

    monkeypatch.setattr("nexo.workspace.run_workspace_query", fake_run_workspace_query)
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexo",
            "workspace",
            "query",
            "how auth works",
            "--workspace",
            str(tmp_path),
            "--mode",
            "central",
            "--dfs",
            "--budget",
            "1200",
            "--top-k",
            "7",
        ],
    )

    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code == 0

    assert captured["workspace_path"] == tmp_path
    assert captured["question"] == "how auth works"
    assert captured["use_dfs"] is True
    assert captured["budget"] == 1200
    assert captured["mode"] == "central"
    assert captured["top_k"] == 7
