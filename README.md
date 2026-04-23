<div align="center">

# nexo

_Turn any folder into a queryable knowledge graph for AI assistants_

[![Release](https://img.shields.io/github/v/release/kenzot25/nexo?style=flat-square)](https://github.com/kenzot25/nexo/releases)
[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white&style=flat-square)](https://www.python.org/)

[Features](#features) • [Quick Start](#quick-start) • [Usage](#usage) • [Commands](#common-commands) • [User Guide](docs/USER_GUIDE.md)

</div>

`nexo` builds a knowledge graph from your codebase and documents, then exposes it via CLI or MCP server. AI assistants can query focused conceptual neighborhoods instead of scanning entire repositories blindly.

## Features

- **Knowledge Graph Generation** - Automatically extracts entities and relationships from source code, docs, and papers
- **MCP Server** - Local server exposing graph tools (resolve, explain, path-find, query) for AI assistants
- **Targeted Queries** - Ask natural language questions about your codebase architecture
- **Multi-Repo Support** - Index and query across multiple repositories in a workspace
- **Incremental Updates** - Watch mode rebuilds graph as you code
- **Claude Code Integration** - PreToolUse hooks guide AI to use graph-first approach

## Quick Start

Get value in under 2 minutes:

### 1. Install

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

### 2. Build the graph

```bash
nexo update .
```

This creates `nexo-out/graph.json` and `nexo-out/GRAPH_REPORT.md`.

### 3. Start MCP server

```bash
nexo mcp nexo-out/graph.json
```

Connect your AI assistant to this MCP server.

### 4. Query the graph

```bash
nexo query "How does authentication connect to the database?"
```

### 5. Verify setup

```bash
nexo doctor
```

## Usage

### Single Project Workflow

```bash
# Build or refresh the graph
nexo update .

# Ask questions
nexo query "What is the main entry point?"
nexo explain "main()"
nexo path "AuthModule" "Database"

# Watch for changes
nexo watch . --debounce 3
```

### Multi-Repo Workspace

```bash
# Index all repos in a folder
nexo workspace ./projects --mode central

# Query across all repos
nexo workspace query "How is logging implemented across services?"
```

### AI Assistant Integration

When your AI assistant has MCP access to nexo:

1. It will check the graph before answering architecture questions
2. It can resolve node names, find paths, and explain connections
3. Verification ensures it actually used the graph (not just file scanning)

```bash
# After an AI session, verify it used MCP tools
nexo verify-subagent --workspace . --mode strict --json
```

## Common Commands

| Command | Description |
|---------|-------------|
| `nexo update .` | Build/rebuild the knowledge graph |
| `nexo query "..."` | Ask a natural language question |
| `nexo explain "NodeName"` | Get details about a specific node |
| `nexo path "A" "B"` | Find shortest path between two concepts |
| `nexo mcp graph.json` | Start MCP server |
| `nexo workspace .` | Index multiple repos |
| `nexo doctor` | Check installation and configuration |
| `nexo watch .` | Auto-rebuild on file changes |

## Documentation

- **[Quickstart](docs/quickstart.md)** - Get started in 2 minutes
- **[User Guide](docs/USER_GUIDE.md)** - Detailed workflows and examples
- **[CLI Reference](docs/CLI_REFERENCE.md)** - Complete command documentation
- **[MCP Guide](docs/MCP_GUIDE.md)** - Using nexo with AI assistants
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions
- **[FAQ](docs/faq.md)** - Frequently asked questions
- **[Architecture](docs/architecture.md)** - How nexo works

## For Developers

Want to contribute or extend nexo?

- **[Developer Guide](docs/DEVELOPING.md)** - Architecture, testing, and adding features
- **[Contributing](docs/CONTRIBUTING.md)** - How to contribute

## Security

nexo runs locally and never sends your code to external services. All graph data stays in `nexo-out/` within your project.

---

_Released under the MIT License._
