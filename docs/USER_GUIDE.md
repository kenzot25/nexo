# User Guide

Complete guide for using nexo to build and query knowledge graphs.

## Installation

### Quick Install (Recommended)

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/kenzot25/nexo/master/scripts/install.sh | sh
```

**Windows:**
```powershell
$script = Join-Path $env:TEMP 'nexo-install.ps1'
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/kenzot25/nexo/master/scripts/install.ps1' -OutFile $script
powershell -ExecutionPolicy Bypass -File $script
```

**Requirements:** Python 3.10+

### Alternative Install Methods

**From GitHub Releases:**
Download the installer zip from [Releases](https://github.com/kenzot25/nexo/releases), extract, and run `install-nexo.command` (macOS) or `install-nexo.bat` (Windows).

**Local Development:**
```bash
git clone https://github.com/kenzot25/nexo.git
cd nexo
make setup
```

## Your First Graph

### Step 1: Build the graph

```bash
cd your-project
nexo update .
```

This creates:
- `nexo-out/graph.json` - The knowledge graph
- `nexo-out/GRAPH_REPORT.md` - Human-readable summary with god nodes and community structure

### Step 2: Explore the report

Open `nexo-out/GRAPH_REPORT.md` to see:
- **God nodes** - Most connected entities (e.g., `main()`, `build_from_json()`)
- **Communities** - Clusters of related code
- **Surprising connections** - Non-obvious relationships discovered

### Step 3: Ask questions

```bash
nexo query "What is the main entry point?"
nexo query "How do auth and transport connect?"
```

### Step 4: Start MCP server (for AI assistants)

```bash
nexo mcp nexo-out/graph.json
```

Your AI assistant can now query the graph via MCP tools.

## Core Workflows

### Querying Your Codebase

**Ask architecture questions:**
```bash
nexo query "Where is authentication handled?"
nexo query "Show me the database layer"
nexo query "What are the core abstractions?"
```

**Use `--dfs` for deeper traversal:**
```bash
nexo query "Trace the request flow" --dfs
```

**Increase token budget for more context:**
```bash
nexo query "Explain the full architecture" --budget 4000
```

### Finding Relationships

**Shortest path between concepts:**
```bash
nexo path "AuthModule" "Database"
nexo path "main()" "cluster()"
```

**Explain a specific node:**
```bash
nexo explain "create_mcp_server"
nexo explain "main()"
```

### Multi-Repo Workspaces

**Index all repos in a folder:**
```bash
nexo workspace ./projects --mode central
```

**Query across all repos:**
```bash
nexo workspace query "How is logging implemented?"
nexo workspace query "Find all HTTP client implementations"
```

**Modes:**
- `--mode central` - Single merged index (recommended)
- `--mode per-repo` - Separate index per repository

### Watching for Changes

**Auto-rebuild on file changes:**
```bash
nexo watch . --debounce 3
```

Options:
- `--debounce N` - Seconds to wait after last change (default: 3)
- `--obsidian-sync` - Also update Obsidian vault if using

## MCP Integration

### Starting the Server

```bash
nexo mcp nexo-out/graph.json
```

The server runs in stdio mode - it waits for an MCP client connection. This is normal behavior.

### Available MCP Tools

When connected, your AI assistant can use:

| Tool | Description |
|------|-------------|
| `resolve_nodes` | Find nodes by fuzzy name match |
| `explain_node` | Explain one node and its connections |
| `shortest_path` | Find path between two nodes |
| `expand_subgraph` | Get bounded neighborhood of nodes |
| `workspace_query` | Query across multiple repos |
| `graph_summary` | Quick overview of graph structure |

### Resources

- `nexo://report` - Full GRAPH_REPORT.md content
- `nexo://summary` - JSON graph summary

### Verifying MCP Usage

After an AI assistant session, verify it actually used the graph:

```bash
nexo verify-subagent --workspace . --mode strict --json
```

**Output:**
```json
{
  "verdict": "PASS",
  "mcp_summary": {
    "total_calls": 4,
    "graph_summary_calls": 1,
    "targeted_query_calls": 3
  },
  "answer_evidence_ok": true,
  "anti_fallback_ok": true
}
```

**With answer text:**
```bash
nexo verify-subagent --workspace . --mode strict \
  --answer "The MCP server exposes 6 tools via FastMCP" --json
```

## Ingesting External Content

**Add a URL to your corpus:**
```bash
nexo add https://example.com/docs/api --author "Your Name"
nexo update .
```

**Options:**
- `--author "Name"` - Tag the original author
- `--contributor "Name"` - Tag who added it
- `--dir ./raw` - Target directory for downloaded content

## Understanding Outputs

### graph.json

The main graph file containing:
- `nodes` - Entities with id, label, source_file, community
- `links` - Relationships with source, target, relation type

### GRAPH_REPORT.md

Human-readable analysis:
- **Community Hubs** - Navigation by code community
- **God Nodes** - Most connected entities
- **Surprising Connections** - Non-obvious relationships
- **Suggested Questions** - Questions the graph can answer

### Other Outputs

- `nexo-out/graph.html` - Interactive visualization
- `nexo-out/wiki/` - Wikipedia-style articles
- `nexo-out/graph.svg` - Static graph diagram

## Common Issues

### "No graph found"

Run `nexo update .` first to build the graph.

### Query returns too little context

- Use a more specific question
- Try `--dfs` instead of default BFS
- Increase `--budget` (e.g., `--budget 4000`)

### MCP server shows no output

This is normal - stdio mode waits for client connection. Press Ctrl+C to stop.

### Verification fails

If `nexo verify-subagent` returns FAIL:
- Check that session log exists: `cat ~/.nexo_session.jsonl`
- Ensure you ran `nexo stats --install-hook` previously
- The AI may have fallen back to file scanning

## Tips for Better Results

1. **Be specific with questions** - "How does auth connect to transport?" works better than "Tell me about auth"

2. **Use node names** - If you know a function/class name, use it: `nexo explain "AuthModule"`

3. **Check GRAPH_REPORT.md first** - Understand your graph structure before querying

4. **Run verify-subagent** - Ensure your AI assistant is actually using the graph

5. **Keep graph updated** - Run `nexo update .` after significant code changes

## Next Steps

- **[CLI Reference](CLI_REFERENCE.md)** - Complete command documentation
- **[MCP Guide](MCP_GUIDE.md)** - Deep dive into MCP integration
- **[Troubleshooting](troubleshooting.md)** - More issues and solutions
- **[FAQ](faq.md)** - Frequently asked questions
