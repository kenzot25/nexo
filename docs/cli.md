# CLI Reference

## Setup and integration

```bash
nexo mcp [graph.json]
nexo install
nexo doctor
nexo claude install
nexo claude uninstall
```

## Graph exploration

```bash
nexo query "<question>" [--dfs] [--budget N] [--graph path]
nexo explain "<node>" [--graph path]
nexo path "<source>" "<target>" [--graph path]
nexo workspace query "<question>" [--workspace path] [--mode auto|per-repo|central]
```

## MCP Usage

`nexo mcp [graph.json]` starts the local MCP stdio server. It exposes structured tools for:

When launched directly in a terminal, the command usually stays running with little or no output because it is waiting for an MCP client. That is normal for stdio transport.

- resolving fuzzy node labels
- explaining one node
- shortest path between two nodes
- bounded subgraph expansion
- workspace-level querying
- compact graph summaries

## Ingestion and updates

```bash
nexo add <url> [--author Name] [--contributor Name] [--dir ./raw]
nexo update <path>
nexo cluster-only <path>
nexo watch <path> [--debounce N] [--obsidian-sync]
nexo workspace <path> [--mode per-repo|central] [--write-gitignore] [--dry-run]
```

## Quality and utility

```bash
nexo benchmark [graph.json]
nexo save-result --question Q --answer A [--nodes N1 N2]
```

## Dev shortcuts (Makefile)

```bash
make setup
make t
make test
make r CMD="python -m pytest tests/ -q --tb=short"
```
