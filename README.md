<div align="center">

# nexo

_Turn any folder into a queryable knowledge graph for AI assistants_

[![Release](https://img.shields.io/github/v/release/kenzot25/nexo?style=flat-square)](https://github.com/kenzot25/nexo/releases)
[![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white&style=flat-square)](https://www.python.org/)

[Features](#features) • [Documentation](#documentation) • [Installation](#installation) • [Usage](#usage) • [Commands](#common-commands)

</div>

`nexo` is a local knowledge-graph engine for AI assistants. It transforms your source files, documentation, and artifacts into a traversable graph that can be consumed from the CLI or through an MCP server. This lets models query focused conceptual neighborhoods instead of scanning entire codebases blindly.

## Features

- 🧠 **Contextual Graph Generation** - Consumes source code, documentation, papers, and formats them into an intelligent graph representation.
- ⚡ **MCP-First Integration** - Run a local MCP server so agents can call explicit graph tools with structured output.
- 🧩 **Skill Compatibility** - Keep Claude-style skill files and hooks when a host still needs slash-command glue.
- 🎯 **Targeted Querying** - Focus your AI's attention accurately using graph relationships, community nodes, and file dependencies.
- 🔄 **Real-Time Updates** - Built-in watchdog daemon allows incremental graph updates on the fly as your codebase evolves.
- 🏢 **Multi-Repo Workspaces** - Manage multiple repositories in a single workspace with centralized or per-repo graph indexing.

## Documentation

Detailed guides and references can be found in the [docs/](docs/) directory:

- [Quickstart](docs/quickstart.md)
- [CLI Reference](docs/cli.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

## Installation

**Requirements:** Python 3.10+

```bash
pip install nexo
```

> [!TIP]
> **Non-technical Install:** Download the installer zip files directly from the GitHub Releases page, extract, and run `install-nexo.command` / `install-nexo.bat`.

### Quick Install Scripts

You can also use one of the quick installation scripts to download and configure the latest release automatically:

**macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/kenzot25/nexo/master/scripts/install.sh | sh
```

**Windows**

```powershell
$script = Join-Path $env:TEMP 'nexo-install.ps1'
Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/kenzot25/nexo/master/scripts/install.ps1' -OutFile $script
powershell -ExecutionPolicy Bypass -File $script
```

If `TEMP`/`TMP` is not set in your session, initialize it first:

```powershell
if (-not $env:TEMP) { $env:TEMP = [System.IO.Path]::GetTempPath() }
if (-not $env:TMP)  { $env:TMP  = $env:TEMP }
```

If you already cloned this repository, run the local installer directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

## Usage

### Quick Start

Initialize nexo in your project, build the graph, and connect an MCP client to it:

```bash
# 1. Build the knowledge graph for the current directory
nexo update .

# 2. Start the local MCP server for this graph
nexo mcp nexo-out/graph.json

# 3. Workspace support (for multiple repos)
nexo workspace . --mode central

# 4. Probe the graph context from the CLI when needed
nexo query "How does auth connect to transport?"
```

For hosts that still expect slash-command workflows, the older skill-based install flow remains available:

```bash
nexo install
nexo claude install
```

> [!NOTE]
> All workflow outputs—including the optimized `graph.json` and a readable `GRAPH_REPORT.md` (which maps god nodes and community structures)—are generated and securely cached under the `nexo-out/` directory.

## Common Commands

Below are the essential subcommands for interacting with and maintaining your localized knowledge graph:

```bash
# Query the graph context using natural language
nexo query "How does auth connect to transport?"

# Get a detailed map and explanation of a specific node
nexo explain "AuthModule"

# Find the shortest conceptual path and relationship between two nodes
nexo path "AuthModule" "Database"

# Import external URL endpoints directly into your raw corpus
nexo add https://example.com/doc --author "Your Name"

# Watch the directory for file modifications and automatically rebuild the graph
nexo watch . --debounce 3

# Manage multi-repo workspaces
nexo workspace /path/to/projects --mode central --write-gitignore

# Query across all repositories in a workspace
nexo workspace query "How is authentication handled across services?"

# Start the MCP stdio server
nexo mcp nexo-out/graph.json
```

> [!CAUTION]
> If you experience integration misconfigurations or hook execution issues with Claude, always run `nexo doctor` to execute a comprehensive diagnostic health check.
