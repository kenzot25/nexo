"""Tests for nexo install --platform routing (Claude scope only)."""
from pathlib import Path
import re
from unittest.mock import patch

import pytest


def _install(tmp_path, platform):
    from nexo.__main__ import install
    with patch("nexo.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)


def test_install_default_claude(tmp_path):
    _install(tmp_path, "claude")
    skill_root = tmp_path / ".claude" / "skills" / "nexo"
    assert (skill_root / "SKILL.md").exists()
    assert any((skill_root / "scripts" / "unix").iterdir())


def test_install_windows(tmp_path):
    _install(tmp_path, "windows")
    skill_root = tmp_path / ".claude" / "skills" / "nexo"
    assert (skill_root / "SKILL.md").exists()
    assert any((skill_root / "scripts" / "windows").iterdir())


def test_install_linked_scripts_resolve(tmp_path):
    _install(tmp_path, "claude")
    skill_root = tmp_path / ".claude" / "skills" / "nexo"
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    links = {
        m.group(1)
        for m in re.finditer(r"\[[^\]]+\]\((scripts/[^)]+)\)", skill_text)
    }
    assert links
    missing = [rel for rel in links if not (skill_root / rel).exists()]
    assert not missing


def test_install_unknown_platform_exits(tmp_path):
    with pytest.raises(SystemExit):
        _install(tmp_path, "unknown")


def test_install_registers_claude_md(tmp_path):
    _install(tmp_path, "claude")
    assert (tmp_path / ".claude" / "CLAUDE.md").exists()


def test_claude_skill_file_exists_in_package():
    import nexo

    pkg = Path(nexo.__file__).parent
    assert (pkg / "skill.md").exists()
    assert (pkg / "skill-windows.md").exists()
    assert any((pkg / "scripts" / "unix").iterdir())
    assert any((pkg / "scripts" / "windows").iterdir())


@pytest.mark.parametrize(
    "script_name",
    [
        "33-for-nexo-query.sh",
        "36-for-nexo-path.sh",
        "39-for-nexo-explain.sh",
        "42-for-nexo-add.sh",
    ],
)
def test_subcommand_scripts_bootstrap_interpreter(script_name):
    import nexo

    pkg = Path(nexo.__file__).parent
    script = pkg / "scripts" / "unix" / script_name
    content = script.read_text(encoding="utf-8")
    assert ".nexo_bin" in content
    assert "command -v nexo" in content


@pytest.mark.parametrize(
    "script_name",
    [
        "31-for-nexo-query.ps1",
        "34-for-nexo-path.ps1",
        "37-for-nexo-explain.ps1",
        "40-for-nexo-add.ps1",
    ],
)
def test_windows_subcommand_scripts_bootstrap_interpreter(script_name):
    import nexo

    pkg = Path(nexo.__file__).parent
    script = pkg / "scripts" / "windows" / script_name
    content = script.read_text(encoding="utf-8")
    assert "Get-Command nexo" in content
    assert ".nexo_bin" in content
