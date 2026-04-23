# FAQ

Frequently asked questions about nexo.

## General

### What problem does nexo solve?

nexo builds a queryable knowledge graph from your source code and documents. Instead of AI assistants scanning entire codebases blindly, they can query focused conceptual neighborhoods using graph relationships.

**Benefits:**
- More accurate answers about architecture
- Reduced token usage
- Faster context retrieval
- Better cross-file understanding

### Is nexo only for Claude Code?

nexo works with any MCP-capable AI assistant. Claude Code integration is provided via:
- PreToolUse hooks that guide graph-first behavior
- Skill files for slash-command workflows

For other assistants, configure the MCP server connection in their settings.

### Do I need an API key?

**No.** nexo runs entirely locally:
- Graph extraction uses tree-sitter (no LLM)
- Query tools use graph traversal (no LLM)
- MCP server is local stdio (no network)

LLM is only needed for optional semantic extraction of documentation.

### Where are outputs stored?

By default in `nexo-out/`:
- `graph.json` - The knowledge graph
- `GRAPH_REPORT.md` - Human-readable analysis
- `wiki/` - Wikipedia-style articles (optional)
- `graph.html` - Interactive visualization (optional)

## Usage

### How do I refresh after code changes?

**Quick update (code files only, no LLM):**
```bash
nexo update .
```

**Full rebuild (includes semantic extraction):**
```bash
nexo update .  # With LLM for docs/papers
```

**Automatic updates:**
```bash
nexo watch . --debounce 3
```

### How do I query across multiple repos?

```bash
# Index all repos in a folder
nexo workspace ./projects --mode central

# Query across all
nexo workspace query "How is logging implemented?"
```

### What file types are supported?

**Code languages:**
- Python, JavaScript, TypeScript
- Go, Rust, Java, C#, C++
- Swift, Kotlin, Ruby, PHP
- And more (tree-sitter based)

**Documents:**
- Markdown, reStructuredText
- PDF (text extraction)
- DOCX (text extraction)
- Web pages (via `nexo add <url>`)

### How accurate are the relationships?

**EXTRACTED edges** - High confidence (explicit in source):
- Import statements
- Direct function calls
- Class inheritance

**INFERRED edges** - Medium confidence (deduced):
- Call-graph second pass
- Co-occurrence in context

**AMBIGUOUS edges** - Low confidence (uncertain):
- Flagged for human review in GRAPH_REPORT.md

## MCP Integration

### How do I connect nexo to my AI assistant?

Configure MCP server in your assistant's settings:

```json
{
  "mcpServers": {
    "nexo": {
      "command": "python",
      "args": ["-m", "nexo.serve", "/absolute/path/to/nexo-out/graph.json"]
    }
  }
}
```

### What if my assistant doesn't support MCP?

nexo includes skill files for Claude Code that work without explicit MCP configuration:

```bash
nexo install --local
nexo claude install
```

The skill provides graph tools via slash-command emulation.

### How do I verify my AI used the graph?

```bash
nexo verify-subagent --workspace . --mode strict --json
```

This checks:
- Session logs for MCP tool calls
- Answer evidence for graph-native terminology
- Anti-fallback patterns (grep/read-only behavior)

## Development

### How do I run tests?

```bash
make t
# or
pytest tests/ -q
```

### How do I add support for a new language?

See [Developer Guide](DEVELOPING.md#adding-a-new-language-extractor) for the complete process.

Summary:
1. Add tree-sitter package
2. Add `extract_<lang>()` function
3. Register file suffix
4. Add tests

### Can I customize the graph output?

Yes, export to multiple formats:

```bash
# Cypher (Neo4j)
nexo internal-export cypher

# Mermaid
nexo internal-export mermaid

# D2
nexo internal-export d2

# Gephi
nexo internal-export gephi

# GraphML
nexo internal-export graphml
```

## Security

### Does nexo send my code to external services?

**No.** Everything runs locally:
- Graph extraction: local tree-sitter
- Query tools: local graph traversal
- MCP server: local stdio transport

### Can I use nexo with private repositories?

**Yes.** The graph stays in `nexo-out/` within your project. You can add it to `.gitignore`:

```bash
echo "nexo-out/" >> .gitignore
```

Or use `--write-gitignore` with workspace:
```bash
nexo workspace . --mode central --write-gitignore
```

### What data is logged?

Session logs (`~/.nexo_session.jsonl`) contain:
- Timestamp
- Tool name
- Workspace path

**No code content or query results are logged.**

## Performance

### How large a codebase can nexo handle?

Tested with:
- 100k+ lines of code
- 1000+ files
- Multiple repositories

For very large codebases:
- Use `.nexoignore` to exclude dependencies
- Increase token budget for queries
- Use targeted queries instead of broad questions

### How long does graph build take?

Depends on corpus size:
- Small project (10 files): ~5 seconds
- Medium project (100 files): ~30 seconds
- Large project (1000 files): ~5 minutes

Code extraction is fast (tree-sitter AST). Document extraction is slower (LLM-based).

### How do I speed up queries?

1. **Use specific node names** - Less traversal needed
2. **Reduce budget** - `--budget 1000` instead of default 2000
3. **Use BFS** - Default, faster than DFS
4. **Start with graph_summary** - Get overview before deep queries

## Troubleshooting

### Where can I get help?

1. **[Troubleshooting Guide](troubleshooting.md)** - Common issues
2. **[GitHub Issues](https://github.com/kenzot25/nexo/issues)** - Search or report bugs
3. **[Discussions](https://github.com/kenzot25/nexo/discussions)** - Ask questions

### What if nexo breaks after an update?

1. **Reinstall skills:**
   ```bash
   nexo install --local
   nexo claude install
   ```

2. **Rebuild graph:**
   ```bash
   nexo update .
   ```

3. **Run doctor:**
   ```bash
   nexo doctor
   ```

---

Still have questions? Open a [Discussion](https://github.com/kenzot25/nexo/discussions) or [Issue](https://github.com/kenzot25/nexo/issues).
