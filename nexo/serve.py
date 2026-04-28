"""MCP server and compatibility exports for nexo graph queries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from networkx.readwrite import json_graph

from nexo import query_service as _qs
from nexo.query_service import (
    _bfs,
    _communities_from_graph,
    _dfs,
    _find_node,
    _score_nodes,
    _strip_diacritics,
    _subgraph_to_text,
    explain_node_query,
    expand_subgraph,
    graph_summary,
    query_graph,
    read_graph_report,
    resolve_nodes,
    shortest_path_query,
)
from nexo.workspace import run_workspace_query

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - exercised indirectly via CLI fallback
    # ImportError or pydantic compatibility issues (e.g., Python 3.14)
    FastMCP = None


SERVER_INSTRUCTIONS = (
    "Use nexo tools only for graph-native operations. "
    "Do not pass broad prose directly to low-level tools. "
    "Resolve uncertain entity names first. "
    "For relationship questions, resolve both entities and then call shortest_path. "
    "For understanding one concept, use explain_node or expand_subgraph. "
    "Prefer short labels or keywords over long natural-language prompts."
)


def _print_stdio_hint_if_interactive() -> None:
    """Explain silent stdio behavior when started manually in a terminal."""
    try:
        if sys.stdin.isatty() and sys.stderr.isatty():
            print(
                "nexo MCP stdio server is running and waiting for a client on stdin/stdout. "
                "No normal output is expected here. Connect it from an MCP-capable host, or press Ctrl+C to stop.",
                file=sys.stderr,
            )
    except Exception:
        return


def _load_graph(graph_path: str):
    """Compatibility wrapper for legacy callers and tests.

    The new query service validates graph roots strictly for MCP and CLI use.
    Legacy serve.py imports historically allowed any readable graph.json path and
    signaled failures via SystemExit, so preserve that here.
    """
    try:
        resolved = Path(graph_path).resolve()
        if resolved.suffix != ".json":
            raise ValueError(f"Graph path must be a .json file, got: {graph_path!r}")
        if not resolved.exists():
            raise FileNotFoundError(f"Graph file not found: {resolved}")
        data = json.loads(resolved.read_text(encoding="utf-8"))
        try:
            return json_graph.node_link_graph(data, edges="links")
        except TypeError:
            return json_graph.node_link_graph(data)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except json.JSONDecodeError as exc:
        print(f"error: graph.json is corrupted ({exc}). Re-run /nexo to rebuild.", file=sys.stderr)
        raise SystemExit(1) from exc


def create_mcp_server(default_graph_path: str = "nexo-out/graph.json"):
    if FastMCP is None:
        raise RuntimeError("The 'mcp' package is required to run the MCP server. Install nexo with its MCP dependency.")

    mcp = FastMCP("nexo", instructions=SERVER_INSTRUCTIONS, json_response=True)

    @mcp.tool(description="Resolve fuzzy labels or keywords into graph nodes with scores.")
    def resolve_nodes_tool(
        query: str,
        graph_path: str | None = None,
        top_k: int = 5,
        include_source: bool = True,
    ) -> dict[str, Any]:
        return resolve_nodes(
            query,
            graph_path=graph_path or default_graph_path,
            top_k=top_k,
            include_source=include_source,
        )

    @mcp.tool(description="Explain one graph node and its strongest local connections.")
    def explain_node(
        node_label_or_id: str,
        graph_path: str | None = None,
        neighbor_limit: int = 20,
    ) -> dict[str, Any]:
        return explain_node_query(
            node_label_or_id,
            graph_path=graph_path or default_graph_path,
            neighbor_limit=neighbor_limit,
        )

    @mcp.tool(description="Find the shortest path between two graph entities.")
    def shortest_path(
        source: str,
        target: str,
        graph_path: str | None = None,
    ) -> dict[str, Any]:
        return shortest_path_query(source, target, graph_path=graph_path or default_graph_path)

    @mcp.tool(description="Expand a bounded graph neighborhood using BFS or DFS.")
    def expand_subgraph_tool(
        seeds: list[str],
        strategy: str = "bfs",
        depth: int = 2,
        token_budget: int = 2000,
        graph_path: str | None = None,
    ) -> dict[str, Any]:
        return expand_subgraph(
            seeds,
            strategy=strategy,
            depth=depth,
            token_budget=token_budget,
            graph_path=graph_path or default_graph_path,
        )

    @mcp.tool(description="Query all graphs in a workspace and merge the top hits.")
    def workspace_query_tool(
        question_or_keywords: str,
        workspace_path: str,
        mode: str = "auto",
        top_k: int = 15,
        budget: int = 2000,
        strategy: str = "bfs",
    ) -> dict[str, Any]:
        return run_workspace_query(
            Path(workspace_path),
            question=question_or_keywords,
            use_dfs=strategy == "dfs",
            budget=budget,
            mode=mode,
            top_k=top_k,
        )

    @mcp.tool(description="Return a compact overview of graph size, communities, and hub nodes.")
    def graph_summary_tool(graph_path: str | None = None) -> dict[str, Any]:
        return graph_summary(graph_path=graph_path or default_graph_path)

    @mcp.resource("nexo://report")
    def graph_report_resource() -> str:
        return read_graph_report(graph_path=default_graph_path)

    @mcp.resource("nexo://summary")
    def graph_summary_resource() -> str:
        return json.dumps(graph_summary(graph_path=default_graph_path), indent=2)

    # ── Conversation graph tools ─────────────────────────────────────────────

    @mcp.tool(description="Check if user input matches multiple intents (ambiguity detection).")
    def conversation_detect_ambiguity(
        user_input: str,
        graph_path: str | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> dict[str, Any]:
        return _qs.detect_ambiguity(
            user_input,
            graph_path=graph_path or default_graph_path,
            top_k=top_k,
            threshold=threshold,
        )

    @mcp.tool(description="Get valid next states from current conversation position.")
    def conversation_next_states(
        current_state: str,
        user_input: str | None = None,
        graph_path: str | None = None,
    ) -> dict[str, Any]:
        return _qs.get_valid_next_states(
            current_state,
            user_input,
            graph_path=graph_path or default_graph_path,
        )

    @mcp.tool(description="Find conversation paths to reach a goal state.")
    def conversation_find_paths(
        goal: str,
        graph_path: str | None = None,
        max_paths: int = 5,
    ) -> dict[str, Any]:
        return _qs.find_conversation_paths(
            goal,
            graph_path=graph_path or default_graph_path,
            max_paths=max_paths,
        )

    @mcp.tool(description="Get recovery path for a failure state.")
    def conversation_get_recovery_path(
        failure_state: str,
        graph_path: str | None = None,
    ) -> dict[str, Any]:
        return _qs.get_recovery_path(
            failure_state,
            graph_path=graph_path or default_graph_path,
        )

    return mcp


def start_server(graph_path: str = "nexo-out/graph.json") -> None:
    _print_stdio_hint_if_interactive()
    create_mcp_server(graph_path).run(transport="stdio")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m nexo.serve")
    parser.add_argument(
        "graph_path",
        nargs="?",
        default="nexo-out/graph.json",
        help="Path to graph.json inside nexo-out/ or workspace-nexo-out/.",
    )
    args = parser.parse_args(argv)
    try:
        start_server(args.graph_path)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()

