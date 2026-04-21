# Architecture

nexo uses a staged pipeline and exposes the result through both CLI commands and a local MCP server:

1. Extract entities/relations from source files and artifacts.
2. Build a graph structure from extracted records.
3. Cluster related nodes into communities.
4. Analyze cohesion, bridges, and high-impact nodes.
5. Export graph outputs (JSON, HTML, Markdown/wiki).
6. Query graph slices for focused assistant context.

## Primary outputs

- `nexo-out/graph.json`
- `nexo-out/GRAPH_REPORT.md`
- Optional wiki and visualization artifacts

## Design goals

- Reduce token usage by querying graph neighborhoods instead of full corpora.
- Keep updates incremental with `nexo update .`.
- Work with local AI hosts via MCP, while keeping Claude project conventions available as compatibility glue.

## Related docs

- `ARCHITECTURE.md`
- `docs/quickstart.md`
- `docs/cli.md`
