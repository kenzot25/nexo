"""Workspace-level orchestration for multi-repo graph generation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from nexo.watch import _rebuild_code


def discover_repositories(workspace_path: Path) -> list[Path]:
    """Find git repositories under a workspace path.

    Includes workspace_path itself when it is a repo. Nested repositories are
    skipped once a parent repo is selected.
    """
    root = workspace_path.resolve()
    repos: list[Path] = []

    def _walk(path: Path) -> None:
        if not path.is_dir():
            return
        git_dir = path / ".git"
        if git_dir.exists():
            repos.append(path)
            return
        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("."):
                continue
            if child.name in {"node_modules", "venv", ".venv", "dist", "build", "target", "nexo-out", "workspace-nexo-out"}:
                continue
            _walk(child)

    _walk(root)
    return repos


def _safe_repo_slug(workspace_path: Path, repo_path: Path) -> str:
    rel = repo_path.resolve().relative_to(workspace_path.resolve())
    if str(rel) == ".":
        return "root"
    slug = str(rel).replace("/", "__")
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", slug) or "root"


def _central_repo_output_dir(workspace_path: Path, repo_path: Path) -> Path:
    """Canonical output dir for a repo in central mode."""
    slug = _safe_repo_slug(workspace_path, repo_path)
    return workspace_path / "workspace-nexo-out" / "repos" / slug


def _load_central_index(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        rows = data.get("repos", data.get("results", []))
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    except Exception:
        return []
    return []


def _ensure_gitignore_entry(repo_path: Path, entry: str, *, dry_run: bool = False) -> bool:
    """Ensure an ignore entry exists. Returns True when a write would occur."""
    gitignore = repo_path / ".gitignore"
    existing = ""
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8", errors="ignore")
        lines = {line.strip() for line in existing.splitlines()}
        if entry in lines:
            return False

    if dry_run:
        return True

    if existing and not existing.endswith("\n"):
        existing += "\n"
    existing += entry + "\n"
    gitignore.write_text(existing, encoding="utf-8")
    return True


def run_workspace_update(
    workspace_path: Path,
    *,
    mode: str = "per-repo",
    write_gitignore: bool = False,
    respect_gitignore: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate/update graphs for all repositories inside a workspace."""
    if mode not in {"per-repo", "central"}:
        raise ValueError("mode must be 'per-repo' or 'central'")

    workspace = workspace_path.resolve()
    repos = discover_repositories(workspace)

    central_root = workspace / "workspace-nexo-out"
    if mode == "central" and not dry_run:
        (central_root / "repos").mkdir(parents=True, exist_ok=True)

    if write_gitignore and mode == "central":
        _ensure_gitignore_entry(workspace, "workspace-nexo-out/", dry_run=dry_run)

    results: list[dict[str, Any]] = []
    for repo in repos:
        out_dir: Path | None
        repo_rel = str(repo.resolve().relative_to(workspace))
        if mode == "per-repo":
            out_dir = None
            output_path = repo / "nexo-out"
            if write_gitignore:
                _ensure_gitignore_entry(repo, "nexo-out/", dry_run=dry_run)
        else:
            output_path = _central_repo_output_dir(workspace, repo)
            out_dir = output_path
            if not dry_run:
                output_path.mkdir(parents=True, exist_ok=True)

        if dry_run:
            results.append(
                {
                    "repo": str(repo),
                    "repo_relative": repo_rel,
                    "repo_slug": _safe_repo_slug(workspace, repo),
                    "ok": True,
                    "output": str(output_path),
                    "graph": str(output_path / "graph.json"),
                    "dry_run": True,
                    "respect_gitignore": respect_gitignore,
                }
            )
            continue

        ok = _rebuild_code(
            repo,
            out_dir=out_dir,
            respect_gitignore=respect_gitignore,
        )
        results.append(
            {
                "repo": str(repo),
                "repo_relative": repo_rel,
                "repo_slug": _safe_repo_slug(workspace, repo),
                "ok": ok,
                "output": str(output_path),
                "graph": str(output_path / "graph.json"),
                "respect_gitignore": respect_gitignore,
            }
        )

    summary = {
        "workspace": str(workspace),
        "mode": mode,
        "respect_gitignore": respect_gitignore,
        "dry_run": dry_run,
        "total_repos": len(repos),
        "ok_repos": sum(1 for r in results if r["ok"]),
        "failed_repos": sum(1 for r in results if not r["ok"]),
        "repos": results,
    }

    if mode == "central":
        summary["index_path"] = str(central_root / "index.json")
        if not dry_run:
            (central_root / "index.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


def run_workspace_query(
    workspace_path: Path,
    *,
    question: str,
    use_dfs: bool = False,
    budget: int = 2000,
    mode: str = "auto",
    top_k: int = 15,
) -> dict[str, Any]:
    """Query all repo graphs in a workspace and merge top hits globally."""
    from nexo.serve import _bfs, _dfs, _load_graph, _score_nodes, _subgraph_to_text

    workspace = workspace_path.resolve()
    terms = [t.lower() for t in question.split() if len(t) > 2]
    if not terms:
        terms = [question.lower()]

    graph_sources: list[tuple[str, Path]] = []
    if mode in {"auto", "central"}:
        index_rows = _load_central_index(workspace / "workspace-nexo-out" / "index.json")
        for row in index_rows:
            graph_path = Path(row.get("graph") or (Path(row.get("output", "")) / "graph.json"))
            repo_label = row.get("repo_relative") or row.get("repo") or str(graph_path.parent)
            if graph_path.exists():
                graph_sources.append((str(repo_label), graph_path))

    if mode in {"auto", "per-repo"} and not graph_sources:
        for repo in discover_repositories(workspace):
            graph_path = repo / "nexo-out" / "graph.json"
            if graph_path.exists():
                rel = str(repo.resolve().relative_to(workspace))
                graph_sources.append((rel, graph_path))

    per_repo: list[dict[str, Any]] = []
    merged_hits: list[dict[str, Any]] = []

    for repo_label, graph_path in graph_sources:
        try:
            G = _load_graph(str(graph_path))
        except SystemExit:
            # _load_graph is CLI-oriented and may sys.exit on invalid files.
            continue

        scored = _score_nodes(G, terms)
        if not scored:
            per_repo.append(
                {
                    "repo": repo_label,
                    "graph": str(graph_path),
                    "matches": 0,
                    "subgraph": "No matching nodes found.",
                }
            )
            continue

        max_score = max(s for s, _ in scored) if scored else 1.0
        start = [nid for _, nid in scored[:5]]
        nodes, edges = (_dfs if use_dfs else _bfs)(G, start, depth=2)

        for score, nid in scored[:top_k]:
            label = G.nodes[nid].get("label", nid)
            merged_hits.append(
                {
                    "repo": repo_label,
                    "score": float(score),
                    "normalized_score": float(score) / float(max_score or 1.0),
                    "node_id": nid,
                    "label": label,
                    "graph": str(graph_path),
                }
            )

        repo_budget = max(300, budget // max(1, len(graph_sources)))
        per_repo.append(
            {
                "repo": repo_label,
                "graph": str(graph_path),
                "matches": len(scored),
                "subgraph": _subgraph_to_text(G, nodes, edges, token_budget=repo_budget),
            }
        )

    merged_hits.sort(key=lambda h: (h["normalized_score"], h["score"], h["label"]), reverse=True)
    merged_hits = merged_hits[:top_k]

    lines: list[str] = []
    lines.append(f"Workspace query: {question}")
    lines.append(f"Repos queried: {len(per_repo)}")
    lines.append("")
    lines.append("Top merged matches:")
    if merged_hits:
        for idx, hit in enumerate(merged_hits, start=1):
            lines.append(
                f"{idx}. [{hit['repo']}] {hit['label']} "
                f"(norm={hit['normalized_score']:.2f}, score={hit['score']:.2f})"
            )
    else:
        lines.append("No matches found across workspace graphs.")

    lines.append("")
    lines.append("Per-repo context:")
    for repo_result in per_repo:
        lines.append(f"## {repo_result['repo']} ({repo_result['matches']} matches)")
        lines.append(repo_result["subgraph"])
        lines.append("")

    text = "\n".join(lines)
    char_budget = max(200, budget * 3)
    if len(text) > char_budget:
        text = text[:char_budget] + f"\n... (truncated to ~{budget} token budget)"

    return {
        "workspace": str(workspace),
        "question": question,
        "mode": mode,
        "repos_queried": len(per_repo),
        "merged_hits": merged_hits,
        "repos": per_repo,
        "text": text,
    }
