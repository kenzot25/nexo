---
name: nexo
description: >
  Use when the user asks to investigate a codebase, understand cross-file relationships, or needs a high-level architecture view.
  This skill is now a bootstrapper for the local nexo MCP server. Use it to build or refresh the graph when needed, then query the graph via MCP tools.
trigger: /nexo
---

# /nexo

Treat this skill as a bridge into MCP, not as the primary query interface.

## Core Rule

If a graph already exists, use the MCP server and MCP tools instead of the old skill-driven `query` / `path` / `explain` workflow.

## Fast Path

If `nexo-out/graph.json` exists:

1. Start or attach the local MCP server for that graph.
2. Call `graph_summary` first for a cheap overview.
3. Use targeted MCP tools to answer the question.
4. Read `nexo-out/GRAPH_REPORT.md` only for broad narrative or architecture-summary questions.
5. If `nexo-out/wiki/index.md` exists, use it only when deeper navigation is needed.
6. Only rebuild if the user asked for a rebuild or the graph is stale after code changes.

## MCP First

Preferred local server command:

```powershell
nexo mcp nexo-out/graph.json
```

Equivalent direct module form:

```powershell
python -m nexo.serve nexo-out/graph.json
```

If the host needs an MCP config snippet, point it at the local server command above and keep the instruction short: use nexo through MCP, not through the old skill query flow.

## MCP Tool Workflow

Use tools in this order:

1. `graph_summary`
Use first for a cheap overview.

2. `resolve_nodes`
Use when labels are uncertain or fuzzy.

3. `explain_node`
Use for one concept after resolving it.

4. `shortest_path`
Use only after you have two resolved concepts.

5. `expand_subgraph`
Use for architecture context, nearby concepts, and bounded traversal.

6. `workspace_query`
Use only for multi-repo questions.

## Query Rules

Do not send vague prose directly to low-level graph tools.

- For “How are A and B related?”: resolve `A`, resolve `B`, then call `shortest_path`.
- For “What does X do?”: resolve `X`, then call `explain_node` or `expand_subgraph`.
- For “Explain the architecture”: call `graph_summary`, then `expand_subgraph` from the main hubs.
- Read `GRAPH_REPORT.md` only when the user wants a broad written summary rather than a targeted graph lookup.
- Use the wiki only when the MCP answer needs deeper document-style navigation.
- Prefer short labels or keywords over full natural-language prompts when calling low-level tools.

## Build Or Refresh

If no graph exists yet, or the user explicitly wants a refresh:

1. Ensure the package is available.

```powershell
python -c "import nexo" 2>$null
if ($LASTEXITCODE -ne 0) { python -m pip install nexo }
```

2. Rebuild or refresh the local code graph.

```powershell
nexo update .
```

3. Start or reconnect the MCP server.

```powershell
nexo mcp nexo-out/graph.json
```

4. Read `GRAPH_REPORT.md` again before answering architecture questions.

If you modified code during this session, run `nexo update .` before further graph queries.

## Fallback When MCP Is Not Connected Yet

If the host has not attached the MCP server yet, you can still use the CLI as a temporary fallback:

```powershell
nexo query "<question>"
nexo explain "<node>"
nexo path "<A>" "<B>"
nexo workspace query "<question>"
```

But this fallback is not the preferred path. Move back to MCP as soon as possible.

## What To Tell The User

When relevant, keep the user-facing guidance short:

- there is already a graph
- MCP is the preferred way to query it
- the best next graph question to explore
- whether a refresh is needed after code changes

## Do Not Do This

- Do not teach the model to ask broad questions directly to low-level tools.
- Do not re-run a rebuild if `nexo-out/graph.json` already exists unless the user asked for it or the graph is stale.
- Do not prefer raw grep/search over the graph for architecture and relationship questions.
- Do not keep using the old skill-driven query steps when MCP is available.

## Success State

You are done when:

- the graph exists or has been refreshed
- the MCP server is the active query path
- the answer is grounded in graph nodes, edges, and local graph context
- the next follow-up question naturally stays within the graph workflow
 

### PowerShell 5.1: Vertical scrolling stops working

If vertical scrolling breaks in PowerShell after running nexo, this is caused by ANSI escape sequences from the `graspologic` library. nexo v0.3.10+ suppresses this output, but if you still see the issue:

1. **Upgrade nexo**: `pip install --upgrade nexo`
2. **Use Windows Terminal** instead of the legacy PowerShell console — Windows Terminal handles ANSI codes correctly
3. **Reset your terminal**: close and reopen PowerShell
4. **Skip graspologic**: uninstall it (`pip uninstall graspologic`) and nexo will fall back to NetworkX's built-in Louvain algorithm, which produces no ANSI output

---

## Honesty Rules

- Never invent an edge. If unsure, use AMBIGUOUS.
- Never skip the corpus check warning.
- Always show token cost in the report.
- Never hide cohesion scores behind symbols - show the raw number.
- Never run HTML viz on a graph with more than 5,000 nodes without warning the user.
