# Quickstart

Get value in under 2 minutes.

## 1. Install

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

## 2. Build a graph

```bash
nexo update .
```

This creates `nexo-out/graph.json` and `nexo-out/GRAPH_REPORT.md`.

## 3. Start the MCP server

```bash
nexo mcp nexo-out/graph.json
```

Connect your AI assistant to this MCP server.

## 4. Verify setup

```bash
nexo doctor
```

## 5. Query the graph

```bash
nexo query "How do auth and transport connect?"
```

## 6. Multi-repo workspaces

For a folder with multiple repositories:

```bash
nexo workspace . --mode central
nexo workspace query "Explain the auth flow across all services"
```

---

## Next Steps

- **[User Guide](USER_GUIDE.md)** - Detailed workflows and examples
- **[CLI Reference](CLI_REFERENCE.md)** - All commands
- **[MCP Guide](MCP_GUIDE.md)** - AI assistant integration
- **[FAQ](faq.md)** - Common questions

## Common Issues

- **`doctor` reports missing skill:** Run `nexo install --local`
- **Hook checks fail:** Run `nexo claude install`
- **`python` not found:** Use `python3` or run `make setup`
- **No graph found:** Run `nexo update .`
