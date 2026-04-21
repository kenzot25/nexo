# Changelog

Full release notes with details on each version: [GitHub Releases](https://github.com/kenzot25/nexo/releases)

## 0.1.0 (2026-04-21)

Initial release of **nexo** — local knowledge-graph engine for AI assistants.

- Multi-language AST extraction via tree-sitter (Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Dart, Verilog and more)
- Leiden community detection with oversized community splitting
- SHA-256 semantic cache — warm re-runs skip unchanged files
- MCP stdio server — `query_graph`, `shortest_path`, `explain_node`, `expand_subgraph`, `graph_summary`
- Obsidian vault export with wikilinks, community tags, and Canvas layout
- Security module — URL validation, safe fetch with size cap, path guards, label sanitisation
- `nexo install` CLI — copies skill to agent config dirs and registers in AGENTS.md / CLAUDE.md
- Watch mode — incremental rebuild on file changes
- Wiki mode — community-aware markdown wiki generation
- Parallel subagent extraction for docs, papers, images, and video transcripts
- Cross-platform installer (Unix + Windows PowerShell)
