"""Token usage stats: graph build cost, query savings, and live session estimate."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_TOKENS_PER_TOOL_CALL = 120  # rough heuristic: input+output overhead per tool invocation
_SESSION_LOG = Path.home() / ".nexo_session.jsonl"

_HOOK_MARKER = "nexo-stats-session"
_HOOK_COMMAND = (
    "python3 -c \""
    "import json, os, sys; "
    "from datetime import datetime, timezone; "
    "tool = os.environ.get('CLAUDE_TOOL_NAME', 'unknown'); "
    "line = json.dumps({'ts': datetime.now(timezone.utc).isoformat(), "
    "'tool': tool, 'workspace': os.getcwd()}); "
    "open(os.path.expanduser('~/.nexo_session.jsonl'), 'a').write(line + chr(10))"
    "\""
)


def load_cost(out_dir: Path) -> dict:
    cost_path = out_dir / "cost.json"
    if not cost_path.exists():
        return {}
    try:
        return json.loads(cost_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_session(session_log: Path) -> list[dict]:
    if not session_log.exists():
        return []
    entries = []
    for line in session_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def _session_since(entries: list[dict]) -> tuple[str | None, list[dict]]:
    """Return (start_ts_label, entries_for_today) filtering to today's date."""
    today = datetime.now(timezone.utc).date().isoformat()
    today_entries = [e for e in entries if e.get("ts", "").startswith(today)]
    if not today_entries:
        return None, []
    start = today_entries[0]["ts"][:16].replace("T", " ")
    return start, today_entries


def print_stats(out_dir: Path, session_log: Path | None = None) -> None:
    sep = "\u2500" * 54
    print(f"\nnexo stats")
    print(sep)

    # --- Graph build cost ---
    cost = load_cost(out_dir)
    if not cost or not cost.get("runs"):
        print("  Graph build cost")
        print("    No cost data yet. Run /nexo first.")
    else:
        runs = cost["runs"]
        total_in = cost.get("total_input_tokens", 0)
        total_out = cost.get("total_output_tokens", 0)
        last = runs[-1]
        last_date = last.get("date", "")[:10]
        last_in = last.get("input_tokens", 0)
        last_out = last.get("output_tokens", 0)
        last_files = last.get("files", 0)
        print(f"  Graph build cost  ({len(runs)} run{'s' if len(runs) != 1 else ''})")
        print(f"    Total input tokens:   {total_in:,}")
        print(f"    Total output tokens:  {total_out:,}")
        print(f"    Last run:  {last_date}  \u2192  {last_in:,} input / {last_out:,} output  ({last_files} files)")

    # --- Token savings ---
    graph_path = out_dir / "graph.json"
    if not graph_path.exists():
        print()
        print("  Token savings")
        print("    No graph.json found — build the graph first.")
    else:
        try:
            from nexo.benchmark import run_benchmark
            detect_path = out_dir / ".nexo_detect.json"
            corpus_words = None
            if detect_path.exists():
                try:
                    corpus_words = json.loads(detect_path.read_text(encoding="utf-8")).get("total_words")
                except Exception:
                    pass
            result = run_benchmark(str(graph_path), corpus_words=corpus_words)
            if "error" in result:
                print()
                print("  Token savings")
                print(f"    {result['error']}")
            else:
                print()
                print(f"  Token savings  (vs naive full-corpus)")
                print(f"    Corpus:        ~{result['corpus_tokens']:,} tokens  (naive)")
                print(f"    Avg per query: ~{result['avg_query_tokens']:,} tokens")
                print(f"    Reduction:     {result['reduction_ratio']}x fewer tokens per query")
        except Exception as exc:
            print()
            print(f"  Token savings")
            print(f"    Could not run benchmark: {exc}")

    # --- Live session ---
    log = session_log or _SESSION_LOG
    entries = _load_session(log)
    start, today_entries = _session_since(entries)
    print()
    if not today_entries:
        print("  Live session")
        print("    No session data. Run: nexo stats --install-hook")
    else:
        call_count = len(today_entries)
        est_tokens = call_count * _TOKENS_PER_TOOL_CALL
        print(f"  Live session  (since {start})")
        print(f"    Tool calls logged:   {call_count}")
        print(f"    Est. session tokens: ~{est_tokens:,}  (based on tool call volume)")

    print(sep)
    print()


def install_hook(settings_path: Path) -> str:
    """Add PostToolUse session logging hook to .claude/settings.json."""
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    post_hooks = hooks.setdefault("PostToolUse", [])

    # Check if already installed
    for entry in post_hooks:
        for h in entry.get("hooks", []):
            if _HOOK_MARKER in h.get("command", ""):
                return "Session hook already installed."

    post_hooks.append({
        "matcher": ".*",
        "hooks": [{"type": "command", "command": _HOOK_COMMAND + f" # {_HOOK_MARKER}"}],
    })

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return f"Session hook installed in {settings_path}. Tool calls will be logged to ~/.nexo_session.jsonl."


def uninstall_hook(settings_path: Path) -> str:
    """Remove PostToolUse session logging hook from .claude/settings.json."""
    if not settings_path.exists():
        return "No .claude/settings.json found — nothing to remove."
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return "Could not parse .claude/settings.json."

    hooks = settings.get("hooks", {})
    post_hooks = hooks.get("PostToolUse", [])
    new_post = []
    removed = 0
    for entry in post_hooks:
        new_entry_hooks = [h for h in entry.get("hooks", []) if _HOOK_MARKER not in h.get("command", "")]
        removed += len(entry.get("hooks", [])) - len(new_entry_hooks)
        if new_entry_hooks:
            new_post.append({**entry, "hooks": new_entry_hooks})

    if removed == 0:
        return "Session hook not found in .claude/settings.json."

    hooks["PostToolUse"] = new_post
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return f"Session hook removed from {settings_path}."
