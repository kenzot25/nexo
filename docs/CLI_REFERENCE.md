# CLI Reference

Complete reference for all nexo commands.

## Setup and Integration

### `nexo install`

Install nexo skills and hooks for AI assistants.

```bash
nexo install [--local] [--platform <name>]
```

**Options:**
- `--local` - Install to current project instead of home directory
- `--platform <name>` - Force platform: `claude`, `windows`

**Example:**
```bash
nexo install --local
```

---

### `nexo doctor`

Validate installation and configuration.

```bash
nexo doctor
```

**Checks:**
- Skill installation
- Skill version
- CLAUDE.md registration
- PreToolUse hook

**Exit codes:**
- `0` - All checks passed
- `1` - One or more checks failed

---

### `nexo claude install`

Write nexo section to CLAUDE.md and install hooks.

```bash
nexo claude install
```

---

### `nexo claude uninstall`

Remove nexo section from CLAUDE.md and hooks.

```bash
nexo claude uninstall
```

---

## Graph Exploration

### `nexo query`

Query the graph with natural language.

```bash
nexo query "<question>" [--dfs] [--budget N] [--graph <path>]
```

**Options:**
- `--dfs` - Use depth-first traversal (default: BFS)
- `--budget N` - Token budget (default: 2000)
- `--graph <path>` - Path to graph.json (default: nexo-out/graph.json)

**Example:**
```bash
nexo query "How does authentication connect to the database?"
nexo query "What are the core abstractions?" --dfs --budget 4000
```

---

### `nexo explain`

Explain a specific node and its connections.

```bash
nexo explain "<node>" [--graph <path>]
```

**Options:**
- `--graph <path>` - Path to graph.json

**Example:**
```bash
nexo explain "main()"
nexo explain "create_mcp_server"
```

---

### `nexo path`

Find shortest path between two nodes.

```bash
nexo path "<source>" "<target>" [--graph <path>]
```

**Options:**
- `--graph <path>` - Path to graph.json

**Example:**
```bash
nexo path "AuthModule" "Database"
nexo path "main()" "cluster()"
```

---

### `nexo workspace query`

Query across multiple repositories.

```bash
nexo workspace query "<question>" \
  [--workspace <dir>] \
  [--mode auto|per-repo|central] \
  [--dfs] \
  [--budget N] \
  [--top-k N]
```

**Options:**
- `--workspace <dir>` - Workspace path (default: .)
- `--mode` - Source mode: `auto`, `per-repo`, `central`
- `--dfs` - Use depth-first traversal
- `--budget N` - Token budget (default: 2000)
- `--top-k N` - Number of merged results (default: 15)

**Example:**
```bash
nexo workspace query "How is logging implemented?" --mode central
```

---

## MCP Server

### `nexo mcp`

Start the MCP stdio server.

```bash
nexo mcp [graph.json]
```

**Arguments:**
- `graph.json` - Path to graph file (default: nexo-out/graph.json)

**Note:** When run directly, the server waits for an MCP client connection. No output is expected until a client connects.

**Example:**
```bash
nexo mcp nexo-out/graph.json
python -m nexo.serve nexo-out/graph.json
```

---

## Ingestion and Updates

### `nexo add`

Fetch a URL and add to corpus.

```bash
nexo add <url> [--author <name>] [--contributor <name>] [--dir <path>]
```

**Options:**
- `--author <name>` - Tag the original author
- `--contributor <name>` - Tag who added it
- `--dir <path>` - Target directory (default: ./raw)

**Example:**
```bash
nexo add https://example.com/docs/api --author "John Doe"
```

---

### `nexo update`

Re-extract code files and update the graph (no LLM needed).

```bash
nexo update <path>
```

**Example:**
```bash
nexo update .
```

---

### `nexo cluster-only`

Rerun clustering on existing graph and regenerate report.

```bash
nexo cluster-only <path>
```

---

### `nexo watch`

Watch for file changes and rebuild graph automatically.

```bash
nexo watch <path> [--debounce N] [--obsidian-sync] [--obsidian-dir <dir>]
```

**Options:**
- `--debounce N` - Seconds to wait after last change (default: 3)
- `--obsidian-sync` - Also refresh Obsidian vault
- `--obsidian-dir <dir>` - Custom Obsidian vault directory

**Example:**
```bash
nexo watch . --debounce 5
nexo watch . --obsidian-sync --obsidian-dir ~/obsidian-vault
```

---

### `nexo workspace`

Generate/update graph for all repos in a workspace.

```bash
nexo workspace <path> \
  [--mode per-repo|central] \
  [--write-gitignore] \
  [--dry-run] \
  [--no-respect-gitignore]
```

**Options:**
- `--mode` - Output mode: `per-repo` (default) or `central`
- `--write-gitignore` - Auto-add graph output to .gitignore
- `--dry-run` - Preview without rebuilding
- `--no-respect-gitignore` - Ignore .gitignore when scanning

**Example:**
```bash
nexo workspace ./projects --mode central --write-gitignore
```

---

## Verification

### `nexo verify-mcp`

Verify AI used nexo MCP tools from session logs.

```bash
nexo verify-mcp \
  [--workspace <dir>] \
  [--session-log <file>] \
  [--window-hours N] \
  [--mode basic|strict] \
  [--min-calls N] \
  [--json]
```

**Options:**
- `--workspace <dir>` - Workspace path (default: .)
- `--session-log <file>` - Session log path (default: ~/.nexo_session.jsonl)
- `--window-hours N` - Lookback window (default: 24)
- `--mode` - `basic` or `strict` (default: strict)
- `--min-calls N` - Minimum MCP calls required (default: 2)
- `--json` - Output machine-readable JSON

**Exit codes:**
- `0` - Verification passed
- `1` - Verification failed

**Example:**
```bash
nexo verify-mcp --mode strict --json
nexo verify-mcp --workspace /path/to/project --window-hours 48
```

---

### `nexo verify-subagent`

Verify MCP usage with subagent-based validation.

```bash
nexo verify-subagent \
  [--workspace <dir>] \
  [--session-log <file>] \
  [--window-hours N] \
  [--mode basic|strict] \
  [--answer <text>] \
  [--json]
```

**Options:**
- `--workspace <dir>` - Workspace path (default: .)
- `--session-log <file>` - Session log path
- `--window-hours N` - Lookback window (default: 24)
- `--mode` - `basic` or `strict` (default: strict)
- `--answer <text>` - Final answer text from main agent
- `--json` - Output machine-readable JSON

**Exit codes:**
- `0` - PASS
- `1` - FAIL

**Example:**
```bash
nexo verify-subagent --mode strict --json
nexo verify-subagent --answer "The graph shows main() as a hub node" --json
```

---

## Utility Commands

### `nexo benchmark`

Measure token reduction vs naive full-corpus approach.

```bash
nexo benchmark [graph.json]
```

---

### `nexo save-result`

Save Q&A result to memory for graph feedback loop.

```bash
nexo save-result \
  --question <Q> \
  --answer <A> \
  [--type query|path_query|explain] \
  [--nodes N1 N2 ...] \
  [--memory-dir <dir>]
```

**Options:**
- `--question <Q>` - The question asked
- `--answer <A>` - The answer to save
- `--type` - Query type (default: query)
- `--nodes` - Source node labels cited in answer
- `--memory-dir` - Memory directory (default: nexo-out/memory)

---

### `nexo stats`

Show token usage: build cost, query savings, session estimate.

```bash
nexo stats [--out-dir <path>] [--install-hook] [--uninstall-hook]
```

**Options:**
- `--out-dir <path>` - Output directory (default: nexo-out)
- `--install-hook` - Add PostToolUse hook for session tracking
- `--uninstall-hook` - Remove the session hook

---

### `nexo hook`

Manage git hooks.

```bash
nexo hook install
nexo hook uninstall
nexo hook status
```

---

## Development Commands

### `make setup`

Set up development environment.

```bash
make setup
```

---

### `make t`

Run all tests.

```bash
make t
```

---

### `make r`

Run arbitrary command in virtualenv.

```bash
make r CMD="python -m pytest tests/test_export.py -q"
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXO_WHISPER_PROMPT` | Prompt for whisper transcription | Auto-generated |

---

## Files and Directories

| Path | Description |
|------|-------------|
| `nexo-out/graph.json` | Main graph file |
| `nexo-out/GRAPH_REPORT.md` | Human-readable report |
| `nexo-out/wiki/` | Wikipedia-style articles |
| `nexo-out/graph.html` | Interactive visualization |
| `~/.nexo_session.jsonl` | Session log for verification |
