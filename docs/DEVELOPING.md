# Developer Guide

For contributors and developers extending nexo.

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/kenzot25/nexo.git
cd nexo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Or use make
make setup
```

### Project Structure

```
nexo/
├── nexo/                    # Main package
│   ├── __main__.py          # CLI entry point
│   ├── serve.py             # MCP server
│   ├── mcp_verify.py        # MCP usage verification
│   ├── mcp_subagent.py      # Subagent-based verification
│   ├── detect.py            # File detection
│   ├── extract.py           # AST extraction
│   ├── build.py             # Graph construction
│   ├── cluster.py           # Community detection
│   ├── analyze.py           # Graph analysis
│   ├── report.py            # Report generation
│   ├── export.py            # Export formats
│   ├── query_service.py     # Query tools
│   ├── workspace.py         # Multi-repo support
│   ├── watch.py             # File watching
│   ├── stats.py             # Token usage stats
│   └── security.py          # Input validation
├── tests/                   # Test suite
├── docs/                    # Documentation
├── scripts/                 # Install scripts
└── pyproject.toml           # Package configuration
```

### Running Tests

```bash
# Run all tests
make t
# or
pytest tests/ -q

# Run specific test file
pytest tests/test_mcp_subagent.py -v

# Run with coverage
pytest tests/ --cov=nexo
```

## Architecture

### Pipeline Stages

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

| Stage | Module | Function | Input → Output |
|-------|--------|----------|----------------|
| Detect | `detect.py` | `collect_files(root)` | directory → `[Path]` |
| Extract | `extract.py` | `extract(path)` | file path → `{nodes, edges}` |
| Build | `build.py` | `build_graph(extractions)` | list of dicts → `nx.Graph` |
| Cluster | `cluster.py` | `cluster(G)` | graph → graph with community attr |
| Analyze | `analyze.py` | `analyze(G)` | graph → analysis dict |
| Report | `report.py` | `render_report(G, analysis)` | graph + analysis → markdown |
| Export | `export.py` | `export(G, out_dir)` | graph → JSON, HTML, wiki |

### Extraction Output Schema

Every extractor returns:

```json
{
  "nodes": [
    {"id": "unique_id", "label": "name", "source_file": "path", "source_location": "L42"}
  ],
  "edges": [
    {"source": "id_a", "target": "id_b", "relation": "calls|imports|uses", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}
  ]
}
```

### Confidence Labels

| Label | Meaning |
|-------|---------|
| `EXTRACTED` | Explicitly stated (e.g., import statement, direct call) |
| `INFERRED` | Reasonable deduction (e.g., call-graph second pass) |
| `AMBIGUOUS` | Uncertain; flagged for review |

## MCP Server Development

### Server Structure

The MCP server in `nexo/serve.py` uses `FastMCP`:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nexo", instructions=SERVER_INSTRUCTIONS)

@mcp.tool(description="...")
def graph_summary_tool(graph_path: str | None = None) -> dict[str, Any]:
    return graph_summary(graph_path=graph_path or default_graph_path)
```

### Available Tools

| Tool | Function | Description |
|------|----------|-------------|
| `resolve_nodes_tool` | `resolve_nodes()` | Fuzzy node label resolution |
| `explain_node` | `explain_node_query()` | Explain one node |
| `shortest_path` | `shortest_path_query()` | Path between two nodes |
| `expand_subgraph_tool` | `expand_subgraph()` | BFS/DFS neighborhood |
| `workspace_query_tool` | `run_workspace_query()` | Multi-repo query |
| `graph_summary_tool` | `graph_summary()` | Graph overview |

### Session Logging

Tool calls are logged to `~/.nexo_session.jsonl`:

```python
# In __main__.py - CLI commands log sessions
entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "tool": "nexo_graph_summary",
    "workspace": str(Path(".").resolve())
}
```

### MCP Verification

The verification system in `nexo/mcp_verify.py` validates AI sessions:

```python
from nexo.mcp_verify import verify_mcp_usage

result = verify_mcp_usage(
    workspace=Path("."),
    mode="strict",  # requires graph_summary + targeted query
    window_hours=24,
)
```

**Subagent verification** (`nexo/mcp_subagent.py`) adds:
- Answer evidence validation
- Anti-fallback detection
- Token usage analysis

## Adding a New Language Extractor

1. **Add tree-sitter dependency** to `pyproject.toml`:
   ```toml
   tree-sitter-xyz = ">=0.1.0"
   ```

2. **Add extractor function** in `nexo/extract.py`:
   ```python
   def extract_xyz(path: Path) -> dict:
       """Extract entities from .xyz files."""
       # Parse with tree-sitter
       # Collect nodes and edges
       # Second pass for INFERRED calls edges
       return {"nodes": [...], "edges": [...]}
   ```

3. **Register file suffix** in dispatch:
   ```python
   if path.suffix == ".xyz":
       return extract_xyz(path)
   ```

4. **Update `CODE_EXTENSIONS`** in `detect.py`:
   ```python
   CODE_EXTENSIONS = {..., ".xyz"}
   ```

5. **Add tests** in `tests/test_languages.py`:
   ```python
   def test_extract_xyz():
       result = extract(Path("fixtures/sample.xyz"))
       assert len(result["nodes"]) > 0
   ```

6. **Add fixture file** to `tests/fixtures/sample.xyz`

## Adding a New MCP Tool

1. **Implement query function** in `nexo/query_service.py`:
   ```python
   def my_new_query(param: str, graph_path: str) -> dict[str, Any]:
       G = _load_graph(graph_path)
       # ... query logic
       return {"result": "...", "text": "..."}
   ```

2. **Register tool** in `nexo/serve.py`:
   ```python
   @mcp.tool(description="My new query tool")
   def my_new_query_tool(param: str, graph_path: str | None = None) -> dict:
       return my_new_query(param, graph_path=graph_path or default_graph_path)
   ```

3. **Add to verification** in `nexo/mcp_verify.py`:
   ```python
   _REQUIRED_TOOLS = {
       # ...
       "my_new_query": ("my_new_query", "mynewquery"),
   }
   ```

4. **Update documentation** in `docs/MCP_GUIDE.md`

## CLI Command Patterns

### Adding a New Command

In `nexo/__main__.py`:

```python
elif cmd == "my-command":
    parser = argparse.ArgumentParser(prog="nexo my-command")
    parser.add_argument("--arg", type=str, default="default")
    args = parser.parse_args(sys.argv[2:])
    
    # Implementation
    result = my_function(args.arg)
    print(result)
```

### Session Logging for New Commands

```python
# After command execution
try:
    from datetime import datetime, timezone
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": "nexo_my_command",
        "workspace": str(Path(".").resolve())
    }
    _DEFAULT_SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _DEFAULT_SESSION_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
except Exception:
    pass
```

## Debugging Tips

### Enable verbose output

```bash
python -m nexo query "test" 2>&1 | head -50
```

### Check graph structure

```python
from networkx.readwrite import json_graph
import json

data = json.loads(Path("nexo-out/graph.json").read_text())
G = json_graph.node_link_graph(data)
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
```

### Inspect session log

```bash
cat ~/.nexo_session.jsonl | tail -20
```

### Test MCP server manually

```bash
# Start server
nexo mcp nexo-out/graph.json

# In another terminal, test with a client
# (depends on your MCP client setup)
```

## Building Releases

### PyInstaller Build

```bash
pyinstaller nexo.spec --clean
```

### Version Management

Update version in:
- `pyproject.toml`
- `nexo/__main__.py` (fallback version detection)

### Publishing to PyPI

```bash
# Build
python -m build

# Upload
twine upload dist/*
```

## Code Style

- Follow PEP 8
- Type hints required for public functions
- Docstrings for modules and public APIs
- Tests for all new features

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull request guidelines.
