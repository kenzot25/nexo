# MCP Guide

Complete guide for using nexo as an MCP server with AI assistants.

## Overview

nexo runs as a local MCP (Model Context Protocol) server, exposing graph-native tools that AI assistants can call directly. This provides structured, efficient access to your codebase architecture.

## Quick Start

```bash
# 1. Build the graph
nexo update .

# 2. Start the MCP server
nexo mcp nexo-out/graph.json

# 3. Connect your AI assistant
# (Configure MCP connection in your assistant's settings)
```

## MCP Tools

The server exposes these tools:

| Tool | Description | Use Case |
|------|-------------|----------|
| `resolve_nodes` | Find nodes by fuzzy name match | "Find the auth module" |
| `explain_node` | Explain one node and neighbors | "What does main() do?" |
| `shortest_path` | Find path between two nodes | "How does A connect to B?" |
| `expand_subgraph` | Get bounded neighborhood | "Show me the auth module's context" |
| `workspace_query` | Query across multiple repos | "Find logging in all services" |
| `graph_summary` | Quick graph overview | "What's in this codebase?" |

## Tool Usage Patterns

### Resolve Nodes (Fuzzy Search)

```python
# MCP tool call
resolve_nodes(query="auth", top_k=5)
```

**When to use:** First step when you have an uncertain node name.

**Response:**
```json
{
  "matches": [
    {"id": "123", "label": "AuthModule", "score": 0.95},
    {"id": "456", "label": "AuthService", "score": 0.87}
  ]
}
```

### Explain Node

```python
explain_node(node_label_or_id="AuthModule", neighbor_limit=20)
```

**When to use:** Understand a specific component and its direct connections.

**Response:**
```json
{
  "node": {"id": "123", "label": "AuthModule", "source_file": "src/auth.py"},
  "neighbors": [...],
  "text": "AuthModule is defined in src/auth.py and connects to..."
}
```

### Shortest Path

```python
shortest_path(source="AuthModule", target="Database")
```

**When to use:** Understand how two components relate.

**Response:**
```json
{
  "path": ["AuthModule", "AuthRepository", "Database"],
  "text": "AuthModule → AuthRepository → Database (2 hops)"
}
```

### Expand Subgraph

```python
expand_subgraph(seeds=["AuthModule"], strategy="bfs", depth=2, token_budget=2000)
```

**When to use:** Get full context around a component.

**Options:**
- `strategy`: "bfs" or "dfs"
- `depth`: How many hops (default: 2)
- `token_budget`: Max tokens to include (default: 2000)

### Workspace Query

```python
workspace_query_tool(
    question_or_keywords="How is authentication implemented?",
    workspace_path="/path/to/projects",
    mode="central",
    top_k=15
)
```

**When to use:** Query across multiple repositories.

### Graph Summary

```python
graph_summary_tool()
```

**When to use:** First call to understand the codebase scope.

**Response:**
```json
{
  "nodes": 1195,
  "edges": 2440,
  "communities": 65,
  "god_nodes": ["main()", "build_from_json()", "detect()"]
}
```

## Resources

MCP resources provide static content:

- `nexo://report` - Full GRAPH_REPORT.md
- `nexo://summary` - JSON graph summary

## Server Instructions for AI Assistants

When configuring your AI assistant, include these instructions:

```
Use nexo tools only for graph-native operations.
Do not pass broad prose directly to low-level tools.
Resolve uncertain entity names first.
For relationship questions, resolve both entities and then call shortest_path.
For understanding one concept, use explain_node or expand_subgraph.
Prefer short labels or keywords over long natural-language prompts.
```

## Verification

### Session Logging

Enable session tracking:

```bash
nexo stats --install-hook
```

This writes tool calls to `~/.nexo_session.jsonl`.

### Verify MCP Usage

After an AI session, verify it actually used the graph:

```bash
# Basic verification (minimum calls)
nexo verify-mcp --workspace . --mode basic --json

# Strict verification (requires graph_summary + targeted query)
nexo verify-mcp --workspace . --mode strict --json

# With subagent (includes answer evidence check)
nexo verify-subagent --workspace . --mode strict --answer "AI's answer here" --json
```

### Exit Codes

- `0` - Verification passed
- `1` - Verification failed

### JSON Output

```json
{
  "verdict": "PASS",
  "mcp_summary": {
    "total_calls": 5,
    "graph_summary_calls": 1,
    "targeted_query_calls": 4,
    "tool_breakdown": {
      "graph_summary": 1,
      "resolve_nodes": 2,
      "explain_node": 2
    }
  },
  "answer_evidence_ok": true,
  "anti_fallback_ok": true,
  "reason": "verification passed with adequate graph-native evidence"
}
```

## Integration Examples

### Claude Code

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "nexo": {
      "command": "python",
      "args": ["-m", "nexo.serve", "/absolute/path/to/nexo-out/graph.json"]
    }
  }
}
```

### Custom MCP Client

```python
from mcp import ClientSession, StdioServerParameters

server_params = StdioServerParameters(
    command="python",
    args=["-m", "nexo.serve", "nexo-out/graph.json"]
)

async with ClientSession(server_params) as session:
    # List available tools
    tools = await session.list_tools()
    
    # Call a tool
    result = await session.call_tool(
        "resolve_nodes",
        arguments={"query": "main", "top_k": 5}
    )
```

## Security Notes

- **Local-first**: Server uses stdio transport, no network exposure
- **Path validation**: Graph paths must be inside `nexo-out/` or `workspace-nexo-out/`
- **Label sanitization**: Control characters stripped, 256 char limit
- **No remote HTTP**: Remote transport intentionally not supported

## Troubleshooting

### Server shows no output

**Normal behavior** - stdio mode waits for client connection. No output until a client connects.

### Connection refused

**Cause:** Server not running or wrong path.

**Fix:**
```bash
# Verify server is running
nexo mcp nexo-out/graph.json

# Check graph file exists
ls -la nexo-out/graph.json
```

### Tool calls return empty results

**Cause:** Graph may be empty or query is too vague.

**Fix:**
```bash
# Rebuild graph
nexo update .

# Try more specific query
resolve_nodes(query="exact_name", top_k=1)
```

### Verification fails

**Cause:** AI assistant fell back to file scanning.

**Fix:**
- Ensure MCP server is connected
- Check session log: `cat ~/.nexo_session.jsonl`
- Re-run `nexo stats --install-hook`

## Best Practices

1. **Start with graph_summary** - Get overview before deep queries
2. **Resolve before explain** - Use `resolve_nodes` for uncertain names
3. **Use short labels** - "main()" not "the main entry point function"
4. **Set token budgets** - Control context size with `--budget` or `token_budget`
5. **Verify sessions** - Run `verify-subagent` after important analyses

## Related Documentation

- [User Guide](USER_GUIDE.md) - General nexo usage
- [CLI Reference](CLI_REFERENCE.md) - All commands
- [Developer Guide](DEVELOPING.md) - Extending MCP server
