from pathlib import Path

from nexo.workspace import discover_repositories, run_workspace_update


def test_discover_repositories_finds_nested_git_repos(tmp_path):
    (tmp_path / "repo-a").mkdir()
    (tmp_path / "repo-a" / ".git").mkdir()
    (tmp_path / "group" / "repo-b").mkdir(parents=True)
    (tmp_path / "group" / "repo-b" / ".git").mkdir()

    repos = discover_repositories(tmp_path)
    repo_set = {p.resolve() for p in repos}

    assert (tmp_path / "repo-a").resolve() in repo_set
    assert (tmp_path / "group" / "repo-b").resolve() in repo_set


def test_run_workspace_update_dry_run_per_repo(monkeypatch, tmp_path):
    repo = tmp_path / "repo-a"
    repo.mkdir()
    (repo / ".git").mkdir()

    called = {"count": 0}

    def fake_rebuild_code(*args, **kwargs):
        called["count"] += 1
        return True

    monkeypatch.setattr("nexo.workspace._rebuild_code", fake_rebuild_code)

    summary = run_workspace_update(tmp_path, mode="per-repo", dry_run=True)

    assert summary["total_repos"] == 1
    assert summary["ok_repos"] == 1
    assert summary["failed_repos"] == 0
    assert called["count"] == 0
    assert summary["repos"][0]["dry_run"] is True
    assert summary["repos"][0]["graph"].endswith("graph.json")


def test_run_workspace_update_central_writes_index(monkeypatch, tmp_path):
    repo = tmp_path / "repo-a"
    repo.mkdir()
    (repo / ".git").mkdir()

    def fake_rebuild_code(*args, **kwargs):
        return True

    monkeypatch.setattr("nexo.workspace._rebuild_code", fake_rebuild_code)

    summary = run_workspace_update(tmp_path, mode="central")

    index_path = tmp_path / "workspace-nexo-out" / "index.json"
    repo_output = tmp_path / "workspace-nexo-out" / "repos" / "repo-a"
    assert summary["total_repos"] == 1
    assert summary["ok_repos"] == 1
    assert index_path.exists()
    assert str(repo_output) == summary["repos"][0]["output"]


def test_run_workspace_update_write_gitignore_per_repo(monkeypatch, tmp_path):
    repo = tmp_path / "repo-a"
    repo.mkdir()
    (repo / ".git").mkdir()

    def fake_rebuild_code(*args, **kwargs):
        return True

    monkeypatch.setattr("nexo.workspace._rebuild_code", fake_rebuild_code)

    run_workspace_update(tmp_path, mode="per-repo", write_gitignore=True)

    gitignore = repo / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert "nexo-out/" in content


def test_run_workspace_update_central_root_repo_slug(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()

    def fake_rebuild_code(*args, **kwargs):
        return True

    monkeypatch.setattr("nexo.workspace._rebuild_code", fake_rebuild_code)

    summary = run_workspace_update(tmp_path, mode="central", dry_run=True)

    assert summary["repos"][0]["repo_slug"] == "root"
    assert summary["repos"][0]["output"].replace("\\", "/").endswith("workspace-nexo-out/repos/root")
