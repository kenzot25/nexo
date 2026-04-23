# Architecture Overview

High-level overview of how nexo works.

For detailed technical documentation, see [Developer Guide](DEVELOPING.md).

## Pipeline

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

| Stage | Description |
|-------|-------------|
| **detect** | Find all files in directory, categorize by type |
| **extract** | Parse files with tree-sitter, extract entities and relationships |
| **build_graph** | Construct NetworkX graph from extractions |
| **cluster** | Detect communities using Leiden algorithm |
| **analyze** | Find god nodes, surprising connections, generate questions |
| **report** | Generate GRAPH_REPORT.md |
| **export** | Write graph.json, HTML, wiki, and other formats |

## Outputs

- `nexo-out/graph.json` - Main graph file (JSON)
- `nexo-out/GRAPH_REPORT.md` - Human-readable analysis
- `nexo-out/graph.html` - Interactive visualization
- `nexo-out/wiki/` - Wikipedia-style articles

## Query Flow

When you run `nexo query "..."`:

1. Parse question for keywords
2. Find matching nodes with `resolve_nodes()`
3. Traverse graph from best matches (BFS or DFS)
4. Stay within token budget
5. Return focused context

## MCP Server

The MCP server (`nexo/serve.py`) exposes graph tools:

- `resolve_nodes` - Fuzzy node search
- `explain_node` - Explain one node
- `shortest_path` - Path between nodes
- `expand_subgraph` - Neighborhood expansion
- `workspace_query` - Multi-repo query
- `graph_summary` - Graph overview

See [MCP Guide](MCP_GUIDE.md) for usage.

## Session Verification

Tool calls are logged to `~/.nexo_session.jsonl`. Verify with:

```bash
nexo verify-subagent --workspace . --mode strict --json
```

See [Developer Guide](DEVELOPING.md) for implementation details.
