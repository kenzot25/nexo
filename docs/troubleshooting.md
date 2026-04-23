# Troubleshooting

Common issues and solutions.

## Installation Issues

### `python` command not found

Use `python3` instead:

```bash
python3 -m nexo --help
```

Or set up the environment:

```bash
make setup
```

### Install script fails

**Check Python version:**
```bash
python3 --version
```

nexo requires Python 3.10+.

**Windows PowerShell execution policy:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `nexo` command not found

After installation, ensure the script directory is in your PATH.

**Check installation:**
```bash
which nexo  # macOS/Linux
where nexo  # Windows
```

**Reinstall:**
```bash
# Run install script again
curl -fsSL https://raw.githubusercontent.com/kenzot25/nexo/master/scripts/install.sh | sh
```

## Doctor Failures

### `skill-installed` fails

```bash
nexo install --local
nexo doctor
```

### `skill-version` fails

```bash
nexo install --local
nexo doctor
```

### `claude-md` fails

```bash
nexo claude install
nexo doctor
```

### `pretool-hook` fails

```bash
nexo claude install
nexo doctor
```

## Graph Issues

### No graph found

```bash
nexo update .
```

### Query returns too little context

1. Use a more specific question
2. Try `--dfs` mode:
   ```bash
   nex0 query "your question" --dfs
   ```
3. Increase token budget:
   ```bash
   nex0 query "your question" --budget 4000
   ```

### GRAPH_REPORT.md is empty

Rebuild the graph:
```bash
nexo update .
```

Check for extraction errors:
```bash
nexo update . 2>&1 | head -50
```

## MCP Server Issues

### Server shows no output

**This is normal.** The MCP server uses stdio transport and waits for a client connection. No output is expected until a client connects.

To stop the server, press `Ctrl+C`.

### Connection refused

**Server not running:**
```bash
# Start the server
nexo mcp nexo-out/graph.json
```

**Wrong graph path:**
```bash
# Verify graph exists
ls -la nexo-out/graph.json

# Use absolute path
nexo mcp /absolute/path/to/nexo-out/graph.json
```

### MCP tools return empty results

**Graph may be empty or outdated:**
```bash
nexo update .
nexo mcp nexo-out/graph.json
```

**Query too vague - use specific node names:**
```bash
# Instead of "auth", try:
resolve_nodes(query="AuthModule", top_k=1)
```

## Verification Issues

### `verify-subagent` returns FAIL

**Check session log exists:**
```bash
cat ~/.nexo_session.jsonl | tail -10
```

**Install session hook if missing:**
```bash
nexo stats --install-hook
```

**AI may have fallen back to file scanning:**
- Ensure MCP server is connected before starting AI session
- Check that AI assistant has MCP tools enabled

### Session log is empty

**Hook not installed:**
```bash
nexo stats --install-hook
```

**Hook installed but not triggered:**
- Restart your AI assistant after installing hook
- Check `.claude/settings.json` has PostToolUse hook

## Workspace Issues

### `nexo workspace` finds no repos

**Check for `.git` directories:**
```bash
find . -name ".git" -type d
```

**Repos without `.git` are not detected.**

### Workspace query returns no results

**Ensure central index exists:**
```bash
ls workspace-nexo-out/graph.json

# If missing, rebuild:
nexo workspace . --mode central
```

## Test Issues

### `pytest` not found

Use the Makefile:
```bash
make t
make r CMD="python -m pytest tests/ -q"
```

Or activate virtual environment:
```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pytest tests/ -q
```

### Tests fail after code changes

**Clear cache and re-run:**
```bash
rm -rf .pytest_cache __pycache__
make t
```

## Performance Issues

### Graph build is slow

**Exclude large directories:**
Create `.nexoignore`:
```
node_modules/
.venv/
build/
dist/
```

**Reduce corpus size:**
```bash
# Only index code files
nexo update .  # Skips large binaries by default
```

### Query is slow

**Use smaller budget:**
```bash
nexo query "question" --budget 1000
```

**Use BFS instead of DFS:**
```bash
nexo query "question"  # Default is BFS, which is faster
```

## Still Having Issues?

1. **Check existing issues:** [GitHub Issues](https://github.com/kenzot25/nexo/issues)
2. **Run doctor:** `nexo doctor`
3. **Check logs:** Review error output with `2>&1`
4. **Open an issue:** Include `nexo doctor` output and error messages
