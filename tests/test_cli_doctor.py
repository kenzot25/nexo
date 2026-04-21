"""CLI tests for doctor command checks and exit codes."""
from pathlib import Path

import pytest


def _write_skill_install(home: Path, version: str) -> None:
    skill_path = home / ".claude" / "skills" / "nexo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("skill", encoding="utf-8")
    (skill_path.parent / ".nexo_version").write_text(version, encoding="utf-8")


def _write_claude_project_files(project: Path, with_hook: bool = True) -> None:
    project.joinpath("CLAUDE.md").write_text("## nexo\n", encoding="utf-8")
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    if with_hook:
        settings.write_text(
            '{"hooks": {"PreToolUse": [{"matcher": "Glob|Grep", "hooks": [{"command": "nexo"}]}]}}',
            encoding="utf-8",
        )
    else:
        settings.write_text('{"hooks": {"PreToolUse": []}}', encoding="utf-8")


def test_doctor_passes_when_all_setup(monkeypatch, tmp_path, capsys):
    from nexo import __main__ as cli

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    _write_skill_install(home, cli.__version__)
    _write_claude_project_files(project, with_hook=True)

    monkeypatch.setattr(cli.Path, "home", lambda: home)

    rc = cli.doctor(project)
    out = capsys.readouterr().out

    assert rc == 0
    assert "[PASS] skill-installed" in out
    assert "[PASS] skill-version" in out
    assert "[PASS] claude-md" in out
    assert "[PASS] pretool-hook" in out


def test_doctor_fails_with_actionable_fixes(monkeypatch, tmp_path, capsys):
    from nexo import __main__ as cli

    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    _write_skill_install(home, "0.0.0")
    _write_claude_project_files(project, with_hook=False)

    monkeypatch.setattr(cli.Path, "home", lambda: home)

    rc = cli.doctor(project)
    out = capsys.readouterr().out

    assert rc == 1
    assert "[FAIL] skill-version" in out
    assert "[FAIL] pretool-hook" in out
    assert "fix: Run 'nexo install' (local or global) to refresh skill files to this package version." in out
    assert "fix: Run 'nexo install --local' to add the PreToolUse hook in .claude/settings.json." in out


def test_cli_doctor_exits_nonzero_on_fail(monkeypatch, capsys):
    from nexo import __main__ as cli

    monkeypatch.setattr("sys.argv", ["nexo", "doctor"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    out = capsys.readouterr().out
    assert exc.value.code == 1
    assert "Doctor found" in out
