# Quickstart

Get first value in under 2 minutes.

## 1. Install

```bash
pip install nexo
```

For local development:

```bash
make setup
```

## 2. Build a graph

```bash
nexo update .
```

## 3. Start the MCP server

```bash
nexo mcp nexo-out/graph.json
```

This exposes graph-native MCP tools like node resolution, explanation, path search, subgraph expansion, workspace query, and graph summary.

## 4. Verify setup

```bash
nexo doctor
```

If your host still depends on slash-command workflows, you can keep the legacy compatibility layer:

```bash
nexo install
nexo claude install
```

## 5. Build and query graph context

```bash
nexo query "How do auth and transport connect?"
```

## 6. Multi-repo workspaces

If you have a folder full of repositories, you can index them all at once:

```bash
nexo workspace . --mode central
nexo workspace query "Explain the auth flow across all services"
```

## Local command shortcuts

The repository includes a `Makefile` that runs commands with `.venv` automatically:

```bash
make t
make test
make r CMD="python -m pytest tests/test_export.py -q"
make run CMD="python -m nexo update ."
```

## Common issues

- If `doctor` reports missing skill/version: run `nexo install` again if you still use the compatibility layer.
- If hook checks fail: run `nexo claude install` again.
- If `python` is missing: use `python3` and `make setup`.
