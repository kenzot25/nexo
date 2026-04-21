"""CLI tests for watch command option parsing."""
from pathlib import Path


def test_watch_forwards_obsidian_options(monkeypatch, tmp_path):
    from nexo import __main__ as cli

    captured: dict = {}

    def fake_watch(path, debounce=3.0, *, obsidian_sync=False, obsidian_dir=None):
        captured["path"] = path
        captured["debounce"] = debounce
        captured["obsidian_sync"] = obsidian_sync
        captured["obsidian_dir"] = obsidian_dir

    monkeypatch.setattr("nexo.watch.watch", fake_watch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexo",
            "watch",
            str(tmp_path),
            "--debounce",
            "1.5",
            "--obsidian-sync",
            "--obsidian-dir",
            str(tmp_path / "vault"),
        ],
    )

    cli.main()

    assert captured["path"] == tmp_path
    assert captured["debounce"] == 1.5
    assert captured["obsidian_sync"] is True
    assert captured["obsidian_dir"] == (tmp_path / "vault")


def test_watch_obsidian_dir_implies_sync(monkeypatch, tmp_path):
    from nexo import __main__ as cli

    captured: dict = {}

    def fake_watch(path, debounce=3.0, *, obsidian_sync=False, obsidian_dir=None):
        captured["obsidian_sync"] = obsidian_sync
        captured["obsidian_dir"] = obsidian_dir

    monkeypatch.setattr("nexo.watch.watch", fake_watch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexo",
            "watch",
            str(tmp_path),
            "--obsidian-dir",
            str(tmp_path / "vault"),
        ],
    )

    cli.main()

    assert captured["obsidian_sync"] is True
    assert captured["obsidian_dir"] == (tmp_path / "vault")
