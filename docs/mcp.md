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

## Verify AI Actually Used MCP

You can verify whether an AI session truly used nexo MCP tools (instead of falling back to plain file scanning):

```bash
nexo verify-mcp --workspace . --mode strict --window-hours 24
```

The command reads `~/.nexo_session.jsonl` by default (written by the `nexo stats --install-hook` PostToolUse hook).

- `strict` mode requires at least one `graph_summary` call and at least one targeted graph query call.
- `basic` mode only requires a minimum number of nexo MCP calls.

Useful options:

```bash
nexo verify-mcp --mode basic --min-calls 1
nexo verify-mcp --session-log /path/to/session.jsonl --json
```

Use the command exit code in CI:

- `0`: verification passed
- `1`: verification failed

## Verifier Subagent (Recommended)

For real project runs, use a dedicated verifier subagent after the main analysis agent finishes.

Verifier subagent checks:

- session evidence: nexo MCP calls exist for the same workspace and time window
- sequence quality: at least `graph_summary` + one targeted query call
- anti-fallback: detect if the run silently switched to grep/read-only behavior
- answer evidence: confirm the final answer references graph-native entities

### CLI Usage

```bash
# Basic verification (requires minimum MCP calls)
nexo verify-subagent --workspace . --mode basic --json

# Strict verification (requires graph_summary + targeted query)
nexo verify-subagent --workspace . --mode strict --window-hours 24 --json

# With answer text for evidence validation
nexo verify-subagent --workspace . --mode strict --answer "The main() function connects Community 1 to Community 2 via BFS traversal" --json
```

### Output Format

JSON output includes:

```json
{
  "verdict": "PASS" | "FAIL",
  "mcp_summary": {
    "total_calls": 5,
    "graph_summary_calls": 1,
    "targeted_query_calls": 4,
    "tool_breakdown": {
      "graph_summary": 1,
      "resolve_nodes": 2,
      "explain_node": 2
    }
  },
  "answer_evidence_ok": true,
  "anti_fallback_ok": true,
  "token_usage_note": "Session used 5 nexo MCP tool(s) for graph-native operations",
  "reason": "verification passed with adequate graph-native evidence"
}
```

### Integration Pattern

After a main analysis agent completes, run the verifier:

```bash
# Capture main agent answer
ANSWER=$(main-agent-output.txt)

# Verify MCP usage
nexo verify-subagent --workspace . --mode strict --answer "$ANSWER" --json | jq .verdict
```

Exit codes:
- `0`: verification passed (PASS)
- `1`: verification failed (FAIL)

### Programmatic Usage

```python
from nexo.mcp_subagent import run_verifier_subagent

result = run_verifier_subagent(
    workspace=Path("."),
    mode="strict",
    answer_text=main_agent_answer,
)

if result["verdict"] == "PASS":
    print("MCP usage validated")
else:
    print(f"Validation failed: {result['reason']}")
```

This subagent-based validation is preferred over isolated unit tests because it verifies real behavior in real sessions.