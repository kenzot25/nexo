"""CLI tests for workspace command option parsing."""


def test_workspace_forwards_options(monkeypatch, tmp_path):
    from nexo import __main__ as cli

    captured = {}

    def fake_run_workspace_update(
        workspace_path,
        *,
        mode="per-repo",
        write_gitignore=False,
        respect_gitignore=True,
        dry_run=False,
    ):
        captured["workspace_path"] = workspace_path
        captured["mode"] = mode
        captured["write_gitignore"] = write_gitignore
        captured["respect_gitignore"] = respect_gitignore
        captured["dry_run"] = dry_run
        return {
            "workspace": str(workspace_path),
            "mode": mode,
            "total_repos": 0,
            "ok_repos": 0,
            "failed_repos": 0,
            "repos": [],
        }

    monkeypatch.setattr("nexo.workspace.run_workspace_update", fake_run_workspace_update)
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexo",
            "workspace",
            str(tmp_path),
            "--mode",
            "central",
            "--write-gitignore",
            "--dry-run",
            "--no-respect-gitignore",
        ],
    )

    cli.main()

    assert captured["workspace_path"] == tmp_path
    assert captured["mode"] == "central"
    assert captured["write_gitignore"] is True
    assert captured["dry_run"] is True
    assert captured["respect_gitignore"] is False
