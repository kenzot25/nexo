# FAQ

## What problem does nexo solve?
It builds a queryable knowledge graph from source and documents so assistants can retrieve focused context instead of scanning everything.

## Is this only for Claude Code?
Current integration targets Claude Code conventions and hooks.

## Where are outputs written?
By default under `nexo-out/`, including `graph.json` and `GRAPH_REPORT.md`.

## How do I refresh after code changes?
Use:

```bash
nexo update .
```

## How do I run commands without activating virtualenv each time?
Use project shortcuts:

```bash
make t
make r CMD="python -m pytest tests/ -q --tb=short"
```
