"""Tests for nexo.mcp_subagent - MCP verification subagent."""

import json
import tempfile
from pathlib import Path

import pytest

from nexo.mcp_subagent import (
    _build_verifier_prompt,
    _DEFAULT_SESSION_LOG,
    run_verifier_subagent,
    verify_mcp_with_subagent,
)


class TestBuildVerifierPrompt:
    """Tests for _build_verifier_prompt function."""

    def test_prompt_contains_workspace(self):
        workspace = Path("/test/workspace")
        prompt = _build_verifier_prompt(
            workspace=workspace,
            session_log=_DEFAULT_SESSION_LOG,
            window_hours=24,
            mode="strict",
        )
        # Path string representation varies by platform (backslash on Windows)
        assert "test" in prompt and "workspace" in prompt

    def test_prompt_contains_session_log(self):
        session_log = Path("/custom/session.jsonl")
        prompt = _build_verifier_prompt(
            workspace=Path("."),
            session_log=session_log,
            window_hours=24,
            mode="strict",
        )
        # Path string representation varies by platform (backslash on Windows)
        assert "custom" in prompt and "session" in prompt

    def test_prompt_contains_window_hours(self):
        prompt = _build_verifier_prompt(
            workspace=Path("."),
            session_log=_DEFAULT_SESSION_LOG,
            window_hours=48,
            mode="basic",
        )
        assert "48" in prompt
        assert "basic" in prompt

    def test_prompt_contains_mode(self):
        prompt = _build_verifier_prompt(
            workspace=Path("."),
            session_log=_DEFAULT_SESSION_LOG,
            window_hours=24,
            mode="strict",
        )
        assert "strict" in prompt

    def test_answer_text_appended(self):
        answer = "This is the main agent's answer about graph nodes."
        prompt = _build_verifier_prompt(
            workspace=Path("."),
            session_log=_DEFAULT_SESSION_LOG,
            window_hours=24,
            mode="strict",
            answer_text=answer,
        )
        assert answer in prompt
        assert "Final answer from main agent:" in prompt

    def test_no_answer_text(self):
        prompt = _build_verifier_prompt(
            workspace=Path("."),
            session_log=_DEFAULT_SESSION_LOG,
            window_hours=24,
            mode="strict",
            answer_text=None,
        )
        assert "Final answer from main agent:" not in prompt


class TestRunVerifierSubagent:
    """Tests for run_verifier_subagent function."""

    def test_verdict_fail_zero_calls(self, tmp_path):
        """Verify FAIL when no MCP calls in session log."""
        # Create empty session log
        session_log = tmp_path / "session.jsonl"
        session_log.write_text("", encoding="utf-8")

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
        )

        assert result["verdict"] == "FAIL"
        assert result["mcp_summary"]["total_calls"] == 0
        assert not result["anti_fallback_ok"]

    def test_verdict_pass_with_calls(self, tmp_path):
        """Verify PASS when MCP calls exist and meet requirements."""
        # Create session log with valid entries
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
            {
                "ts": "2026-04-23T10:02:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_explain_node",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
        )

        assert result["verdict"] == "PASS"
        assert result["mcp_summary"]["total_calls"] >= 2
        assert result["mcp_summary"]["graph_summary_calls"] >= 1

    def test_answer_evidence_with_graph_keywords(self, tmp_path):
        """Verify answer evidence detection with graph terminology."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        answer = "The main() function is a hub node connecting multiple communities via BFS traversal."

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
            answer_text=answer,
        )

        assert result["answer_evidence_ok"] is True

    def test_answer_evidence_without_graph_keywords(self, tmp_path):
        """Verify answer evidence fails without graph terminology."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        answer = "The code is in the main file and uses standard patterns."

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
            answer_text=answer,
        )

        assert result["answer_evidence_ok"] is False

    def test_strict_mode_requires_graph_summary(self, tmp_path):
        """Verify strict mode fails without graph_summary call."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_explain_node",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
        )

        # Should fail strict mode (no graph_summary)
        assert result["verdict"] == "FAIL"

    def test_basic_mode_passes_with_min_calls(self, tmp_path):
        """Verify basic mode passes with minimum calls."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_explain_node",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="basic",
        )

        # Basic mode should pass with 2 calls even without graph_summary
        assert result["verdict"] == "PASS"

    def test_mcp_summary_structure(self, tmp_path):
        """Verify mcp_summary has correct structure."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
        )

        summary = result["mcp_summary"]
        assert "total_calls" in summary
        assert "graph_summary_calls" in summary
        assert "targeted_query_calls" in summary
        assert "tool_breakdown" in summary
        assert isinstance(summary["tool_breakdown"], dict)


class TestVerifyMcpWithSubagent:
    """Tests for verify_mcp_with_subagent function."""

    def test_returns_exit_code_zero_on_pass(self, tmp_path, capsys):
        """Verify exit code 0 on PASS."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result, exit_code = verify_mcp_with_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="basic",
        )

        assert exit_code == 0
        assert result["verdict"] == "PASS"

    def test_returns_exit_code_one_on_fail(self, tmp_path, capsys):
        """Verify exit code 1 on FAIL."""
        session_log = tmp_path / "session.jsonl"
        session_log.write_text("", encoding="utf-8")

        result, exit_code = verify_mcp_with_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
        )

        assert exit_code == 1
        assert result["verdict"] == "FAIL"

    def test_json_output_format(self, tmp_path, capsys):
        """Verify JSON output format."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result, exit_code = verify_mcp_with_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="basic",
            as_json=True,
        )

        captured = capsys.readouterr()
        # Should print valid JSON
        parsed = json.loads(captured.out)
        assert "verdict" in parsed
        assert "mcp_summary" in parsed
        assert "answer_evidence_ok" in parsed

    def test_human_readable_output(self, tmp_path, capsys):
        """Verify human-readable output format."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        result, exit_code = verify_mcp_with_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="basic",
            as_json=False,
        )

        captured = capsys.readouterr()
        assert "[PASS]" in captured.out or "[FAIL]" in captured.out
        assert "workspace:" in captured.out
        assert "MCP calls:" in captured.out


class TestAntiFallbackDetection:
    """Tests for anti-fallback detection logic."""

    def test_detects_fallback_when_claims_graph_but_zero_calls(self, tmp_path):
        """Verify detection when answer claims graph usage but zero MCP calls."""
        session_log = tmp_path / "session.jsonl"
        session_log.write_text("", encoding="utf-8")

        answer = "Based on the graph analysis, the main() function is a hub node."

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
            answer_text=answer,
        )

        assert result["anti_fallback_ok"] is False
        assert result["verdict"] == "FAIL"

    def test_passes_when_graph_calls_match_answer(self, tmp_path):
        """Verify PASS when MCP calls support answer claims."""
        session_log = tmp_path / "session.jsonl"
        entries = [
            {
                "ts": "2026-04-23T10:00:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_graph_summary",
            },
            {
                "ts": "2026-04-23T10:01:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_resolve_nodes",
            },
            {
                "ts": "2026-04-23T10:02:00Z",
                "workspace": str(tmp_path),
                "tool": "nexo_explain_node",
            },
        ]
        session_log.write_text(
            "\n".join(json.dumps(e) for e in entries),
            encoding="utf-8",
        )

        answer = "The graph shows main() as a hub node with 43 edges connecting communities."

        result = run_verifier_subagent(
            workspace=tmp_path,
            session_log=session_log,
            window_hours=24,
            mode="strict",
            answer_text=answer,
        )

        assert result["anti_fallback_ok"] is True
        assert result["answer_evidence_ok"] is True
