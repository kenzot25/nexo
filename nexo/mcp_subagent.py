"""MCP verification subagent - validates AI sessions used nexo MCP tools correctly."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .mcp_verify import verify_mcp_usage

_DEFAULT_SESSION_LOG = Path.home() / ".nexo_session.jsonl"

VERIFIER_PROMPT_TEMPLATE = """You are a verifier subagent for nexo MCP usage.

Your task is to verify whether the main analysis agent genuinely used nexo MCP tools
instead of falling back to plain file scanning or grep-based search.

Inputs:
1) Workspace path: {workspace}
2) Session log: {session_log}
3) Window: last {window_hours} hours
4) Mode: {mode} (basic requires min calls, strict requires graph_summary + targeted query)

Steps:
1. Run verification command:
   nexo verify-mcp --workspace {workspace} --mode {mode} --window-hours {window_hours} --json

2. Analyze the JSON result for:
   - mcp_calls count
   - tool_counts breakdown (graph_summary, resolve_nodes, explain_node, shortest_path, etc.)
   - missing requirements list

3. Check for anti-fallback patterns:
   - If mcp_calls == 0 but answer exists → likely fallback to grep/read
   - If only graph_summary but no targeted queries → superficial usage
   - If session log has gaps during the analysis window → possible tool switching

4. Validate answer evidence (if answer text provided):
   - Look for graph-native entity references (node labels, community IDs, paths)
   - Check for mentions of graph structure (edges, nodes, communities, hubs)
   - Flag answers that read like generic file search results

Output JSON:
{{
    "verdict": "PASS" | "FAIL",
    "mcp_summary": {{
        "total_calls": <int>,
        "graph_summary_calls": <int>,
        "targeted_query_calls": <int>,
        "tool_breakdown": {{<tool>: <count>, ...}}
    }},
    "answer_evidence_ok": true | false | "not_provided",
    "anti_fallback_ok": true | false,
    "token_usage_note": "<optional note about token efficiency>",
    "reason": "<concise explanation of verdict>"
}}

Rules:
- PASS only if verification command returns pass=true AND answer evidence is adequate
- FAIL if verification fails (missing graph_summary, insufficient calls, etc.)
- FAIL if answer has no graph-native evidence (nodes/paths/communities mentioned)
- FAIL if answer claims graph usage but verification shows zero nexo MCP calls
- Be strict: falling back to grep without explanation is a validation failure
"""


def _build_verifier_prompt(
    workspace: Path,
    session_log: Path,
    window_hours: int,
    mode: str,
    answer_text: str | None = None,
) -> str:
    """Build the verifier subagent prompt."""
    prompt = VERIFIER_PROMPT_TEMPLATE.format(
        workspace=workspace,
        session_log=session_log,
        window_hours=window_hours,
        mode=mode,
    )

    if answer_text:
        prompt += f"\n\nFinal answer from main agent:\n---\n{answer_text}\n---\n"

    return prompt


def run_verifier_subagent(
    workspace: Path,
    session_log: Path | None = None,
    window_hours: int = 24,
    mode: str = "strict",
    answer_text: str | None = None,
) -> dict[str, Any]:
    """Run the verifier subagent to validate MCP tool usage.

    Args:
        workspace: Path to the workspace that was analyzed
        session_log: Path to session log (default: ~/.nexo_session.jsonl)
        window_hours: Time window in hours to check
        mode: Verification mode ('basic' or 'strict')
        answer_text: Optional final answer text from main agent

    Returns:
        Verification result dict with verdict, mcp_summary, answer_evidence_ok, etc.
    """
    session_log = session_log or _DEFAULT_SESSION_LOG

    # First, run the base verification
    base_result = verify_mcp_usage(
        workspace=workspace,
        session_log=session_log,
        window_hours=window_hours,
        mode=mode,
    )

    # Build verifier prompt
    prompt = _build_verifier_prompt(
        workspace=workspace.resolve(),
        session_log=session_log,
        window_hours=window_hours,
        mode=mode,
        answer_text=answer_text,
    )

    # Analyze answer evidence if provided
    answer_evidence_ok = True
    anti_fallback_ok = True
    token_usage_note = ""
    reason_parts = []

    if answer_text:
        # Check for graph-native entity references
        graph_keywords = [
            "node", "edge", "community", "graph", "path", "hub",
            "cluster", "adjacent", "neighbor", "bfs", "dfs", "traversal",
        ]
        answer_lower = answer_text.lower()
        graph_refs = sum(1 for kw in graph_keywords if kw in answer_lower)

        if graph_refs < 2:
            answer_evidence_ok = False
            reason_parts.append("answer lacks graph-native terminology")

        # Check if answer claims to use graph but verification shows no calls
        if "graph" in answer_lower and base_result["mcp_calls"] == 0:
            anti_fallback_ok = False
            reason_parts.append("answer mentions graph but zero MCP calls detected")

    # Validate anti-fallback
    if base_result["mcp_calls"] == 0 and not answer_text:
        # Can't verify without answer, but zero calls is suspicious
        anti_fallback_ok = False
        reason_parts.append("no MCP tool calls in session log")

    # Check for strict mode requirements
    if mode == "strict":
        if base_result["mcp_calls"] < 2:
            anti_fallback_ok = False
            reason_parts.append("strict mode requires at least 2 MCP calls")

    # Token usage note
    if base_result["mcp_calls"] > 0:
        token_usage_note = f"Session used {base_result['mcp_calls']} nexo MCP tool(s) for graph-native operations"
        if base_result["tool_counts"].get("graph_summary", 0) > 0:
            token_usage_note += "; graph_summary provides cheap overview before targeted queries"

    # Determine verdict
    verdict = "PASS" if (
        base_result["pass"] and
        answer_evidence_ok and
        anti_fallback_ok
    ) else "FAIL"

    if base_result["pass"] and not reason_parts:
        reason_parts.append("verification passed with adequate graph-native evidence")

    # Build MCP summary
    mcp_summary = {
        "total_calls": base_result["mcp_calls"],
        "graph_summary_calls": base_result["tool_counts"].get("graph_summary", 0),
        "targeted_query_calls": sum(
            base_result["tool_counts"].get(t, 0)
            for t in ["resolve_nodes", "explain_node", "shortest_path", "expand_subgraph", "workspace_query"]
        ),
        "tool_breakdown": base_result["tool_counts"],
    }

    return {
        "verdict": verdict,
        "mcp_summary": mcp_summary,
        "answer_evidence_ok": answer_evidence_ok,
        "anti_fallback_ok": anti_fallback_ok,
        "token_usage_note": token_usage_note,
        "reason": "; ".join(reason_parts) if reason_parts else "verification passed",
        "base_verification": base_result,
    }


def verify_mcp_with_subagent(
    workspace: Path,
    session_log: Path | None = None,
    window_hours: int = 24,
    mode: str = "strict",
    answer_text: str | None = None,
    as_json: bool = False,
) -> tuple[dict[str, Any], int]:
    """Run MCP verification with subagent and return result with exit code.

    Args:
        workspace: Path to the workspace that was analyzed
        session_log: Path to session log (default: ~/.nexo_session.jsonl)
        window_hours: Time window in hours to check
        mode: Verification mode ('basic' or 'strict')
        answer_text: Optional final answer text from main agent
        as_json: If True, return machine-readable JSON

    Returns:
        Tuple of (result dict, exit code)
        Exit code: 0 for PASS, 1 for FAIL
    """
    result = run_verifier_subagent(
        workspace=workspace,
        session_log=session_log,
        window_hours=window_hours,
        mode=mode,
        answer_text=answer_text,
    )

    exit_code = 0 if result["verdict"] == "PASS" else 1

    if as_json:
        # Remove base_verification from JSON output for cleaner response
        output = {k: v for k, v in result.items() if k != "base_verification"}
        output["base_verification_pass"] = result["base_verification"]["pass"]
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        lines = [
            f"[{result['verdict']}] MCP Subagent Verification",
            f"  workspace: {workspace.resolve()}",
            f"  session log: {session_log or _DEFAULT_SESSION_LOG}",
            f"  window: last {window_hours}h",
            f"  mode: {mode}",
            f"  MCP calls: {result['mcp_summary']['total_calls']}",
            f"    - graph_summary: {result['mcp_summary']['graph_summary_calls']}",
            f"    - targeted queries: {result['mcp_summary']['targeted_query_calls']}",
            f"  answer evidence: {'OK' if result['answer_evidence_ok'] else 'MISSING'}",
            f"  anti-fallback: {'OK' if result['anti_fallback_ok'] else 'FAILED'}",
        ]
        if result["token_usage_note"]:
            lines.append(f"  token usage: {result['token_usage_note']}")
        lines.append(f"  reason: {result['reason']}")
        print("\n".join(lines))

    return result, exit_code


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for MCP subagent verification."""
    import argparse

    parser = argparse.ArgumentParser(prog="nexo verify-subagent")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("."),
        help="Workspace path to match log entries (default: .)",
    )
    parser.add_argument(
        "--session-log",
        type=Path,
        default=None,
        help="Session log path (default: ~/.nexo_session.jsonl)",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Lookback window in hours (default: 24)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="strict",
        choices=["basic", "strict"],
        help="Verification mode (default: strict)",
    )
    parser.add_argument(
        "--answer",
        type=str,
        default=None,
        help="Final answer text from main agent (optional)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print machine-readable JSON result",
    )

    args = parser.parse_args(argv)

    try:
        _, exit_code = verify_mcp_with_subagent(
            workspace=args.workspace,
            session_log=args.session_log,
            window_hours=args.window_hours,
            mode=args.mode,
            answer_text=args.answer,
            as_json=args.as_json,
        )
        return exit_code
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
