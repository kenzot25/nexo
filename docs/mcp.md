# MCP Guide

`nexo` can run as a local MCP server so agents call explicit graph tools instead of relying on skill prompts.

## Start the server

```bash
nexo update .
nexo mcp nexo-out/graph.json
```

You can also start it directly:

```bash
python -m nexo.serve nexo-out/graph.json
```

When started manually, stdio mode may appear to "do nothing". That is expected: the process stays running and waits for an MCP client over stdin/stdout.

## Tool model

The MCP server is graph-native, not free-form QA first.

- Resolve fuzzy names with `resolve_nodes`
- Explain one concept with `explain_node`
- Connect two concepts with `shortest_path`
- Load bounded architecture context with `expand_subgraph`
- Query across repositories with `workspace_query`
- Get a cheap overview with `graph_summary`

## Recommended server instructions

Use nexo tools only for graph-native operations.
Do not pass broad prose directly to low-level tools.
Resolve uncertain entity names first.
For relationship questions, resolve both entities and then call `shortest_path`.
For understanding one concept, use `explain_node` or `expand_subgraph`.
Prefer short labels or keywords over long natural-language prompts.

## Resources

- `nexo://report`
- `nexo://summary`

## Security notes

- The server is local-first and uses stdio.
- Graph paths must stay inside `nexo-out/` or `workspace-nexo-out/`.
- Labels are sanitized before text output.
- Remote HTTP transport is intentionally not part of the default flow.