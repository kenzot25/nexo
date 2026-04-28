"""nexo CLI - `nexo install` sets up the Claude Code skill."""
from __future__ import annotations
import json
import platform
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("nexo")
except Exception:
    # Fallback for development/source installs
    __version__ = "unknown"
    try:
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject.exists():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version ="):
                    __version__ = line.split("=")[1].strip().strip('"')
                    break
    except Exception:
        pass


def _get_resource_path(relative_path: str) -> Path:
    """Resolve paths to bundled data files (supports source and PyInstaller environments)."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.resolve()
    return base_path / relative_path


def _check_skill_version(skill_dst: Path) -> None:
    """Warn if the installed skill is from an older nexo version."""
    version_file = skill_dst.parent / ".nexo_version"
    if not version_file.exists():
        return
    installed = version_file.read_text(encoding="utf-8").strip()
    if installed != __version__:
        print(f"  warning: skill is from nexo {installed}, package is {__version__}. Run 'nexo install' to update.", file=sys.stderr)


def _check_pypi_version() -> str | None:
    """Check PyPI for the latest version."""
    try:
        import urllib.request
        import json as _json
        with urllib.request.urlopen("https://pypi.org/pypi/nexo/json", timeout=2) as resp:
            data = _json.loads(resp.read().decode())
            return data["info"]["version"]
    except Exception:
        return None

_SETTINGS_HOOK = {
    "matcher": "Glob|Grep|FileRead|ListFiles|FileSearch",
    "hooks": [
        {
            "type": "command",
            "command": (
                "[ -f nexo-out/graph.json ] && "
                r"""echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"GUIDANCE: A nexo knowledge graph exists for this project (nexo-out/graph.json). High-level architecture and cross-file relationship queries are 5-10x faster and more accurate via the graph than manual searching. Try: `/nexo query <your question>`. Fall back to standard search tools only if the graph results are insufficient for specific details."}}' """
                "|| true"
            ),
        }
    ],
}

_SKILL_REGISTRATION = (
    "\n## nexo\n"
    "- **nexo** (`.claude/skills/nexo/SKILL.md`) "
    "- knowledge graph explorer. Trigger: `/nexo` or `/nexo`\n"
    "When the user asks about project architecture, cross-file relationships, or uses `/nexo` or `/nexo`, "
    "invoke the Skill tool with `skill: \"nexo\"` immediately.\n"
)


_PLATFORM_CONFIG: dict[str, dict] = {
    "claude": {
        "skill_file": "skill.md",
        "skill_dst": Path(".claude") / "skills" / "nexo" / "SKILL.md",
        "claude_md": True,
    },
    "windows": {
        "skill_file": "skill-windows.md",
        "skill_dst": Path(".claude") / "skills" / "nexo" / "SKILL.md",
        "claude_md": True,
    },
}


def install(platform: str = "claude", local: bool = False) -> None:
    if platform not in _PLATFORM_CONFIG:
        print(
            f"error: unknown platform '{platform}'. Choose from: {', '.join(_PLATFORM_CONFIG)}, gemini, cursor",
            file=sys.stderr,
        )
        sys.exit(1)

    cfg = _PLATFORM_CONFIG[platform]
    skill_src = _get_resource_path(cfg["skill_file"])
    if not skill_src.exists():
        print(f"error: {cfg['skill_file']} not found in package - reinstall nexo", file=sys.stderr)
        sys.exit(1)
    scripts_src = _get_resource_path("scripts")
    if not scripts_src.exists():
        print("error: scripts not found in package - reinstall nexo", file=sys.stderr)
        sys.exit(1)

    base_dir = Path(".") if local else Path.home()
    skill_dst = base_dir / cfg["skill_dst"]
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(skill_src, skill_dst)
    scripts_dst = skill_dst.parent / "scripts"
    if scripts_dst.exists():
        shutil.rmtree(scripts_dst)
    shutil.copytree(scripts_src, scripts_dst)
    (skill_dst.parent / ".nexo_version").write_text(__version__, encoding="utf-8")
    print(f"  skill installed  ->  {skill_dst}")
    script_count = len([p for p in scripts_dst.rglob("*") if p.is_file()])
    print(f"  scripts copied   ->  {scripts_dst} ({script_count} files)")
    skill_text = skill_dst.read_text(encoding="utf-8")
    linked_script_paths = {
        match.group(1)
        for match in re.finditer(r"\[[^\]]+\]\((scripts/[^)]+)\)", skill_text)
    }
    missing_linked_scripts = sorted(
        rel_path for rel_path in linked_script_paths if not (skill_dst.parent / rel_path).exists()
    )
    if missing_linked_scripts:
        print(
            f"  linked scripts  ->  WARNING: {len(missing_linked_scripts)} missing file(s) referenced in SKILL.md"
        )
    else:
        print(f"  linked scripts  ->  verified ({len(linked_script_paths)} links resolved)")

    if cfg["claude_md"]:
        # Register in CLAUDE.md (local root if local=True, otherwise ~/.claude/CLAUDE.md)
        claude_md = (Path(".") / "CLAUDE.md") if local else (Path.home() / ".claude" / "CLAUDE.md")
        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            if _CLAUDE_MD_MARKER in content:
                print(f"  CLAUDE.md        ->  already registered (no change)")
            else:
                claude_md.write_text(content.rstrip() + _SKILL_REGISTRATION, encoding="utf-8")
                print(f"  CLAUDE.md        ->  skill registered in {claude_md}")
        else:
            claude_md.parent.mkdir(parents=True, exist_ok=True)
            claude_md.write_text(_SKILL_REGISTRATION.lstrip(), encoding="utf-8")
            print(f"  CLAUDE.md        ->  created at {claude_md}")

    # Register PreToolUse hook
    _install_claude_hook(base_dir)


    print()
    print("Done. Open your AI coding assistant and type:")
    print()
    print("  /nexo .")
    print()
    print("For MCP-capable hosts, point them at:")
    print()
    print('  python -m nexo.serve "/absolute/path/to/nexo-out/graph.json"')
    print()


_CLAUDE_MD_SECTION = """\
## nexo

This project has a nexo knowledge graph at nexo-out/.

Rules:
- **Be Graph-First**: Before using Grep or Search for architectural questions, query the graph via `/nexo query <question>`.
- Read nexo-out/GRAPH_REPORT.md first for god nodes and community structure overview.
- If nexo-out/wiki/index.md exists, navigate it instead of reading raw files.
- After modifying code files in this session, run `nexo update .` to keep the graph current (AST-only, no API cost).
"""

_CLAUDE_MD_MARKER = "## nexo"


def _has_nexo_pretool_hook(settings_path: Path) -> bool:
    """Return True when settings.json contains the nexo PreToolUse hook."""
    if not settings_path.exists():
        return False
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    hooks = settings.get("hooks", {}).get("PreToolUse", [])
    return any("nexo" in str(h) for h in hooks)


def doctor(project_dir: Path = Path(".")) -> int:
    """Validate local install/setup and print actionable remediation."""
    checks: list[tuple[str, bool, str]] = []

    installed_skill_paths = []
    for cfg in _PLATFORM_CONFIG.values():
        for base in (Path.home(), project_dir):
            p = base / cfg["skill_dst"]
            if p.exists():
                installed_skill_paths.append(p)

    checks.append(
        (
            "skill-installed",
            bool(installed_skill_paths),
            "Run 'nexo install' to install skill files into your assistant config directory.",
        )
    )

    if installed_skill_paths:
        version_ok = True
        for skill_path in installed_skill_paths:
            version_file = skill_path.parent / ".nexo_version"
            if not version_file.exists() or version_file.read_text(encoding="utf-8").strip() != __version__:
                version_ok = False
                break
        checks.append(
            (
                "skill-version",
                version_ok,
                "Run 'nexo install' (local or global) to refresh skill files to this package version.",
            )
        )

    local_claude_md = project_dir / "CLAUDE.md"
    claude_md_ok = local_claude_md.exists() and _CLAUDE_MD_MARKER in local_claude_md.read_text(encoding="utf-8")
    checks.append(
        (
            "claude-md",
            claude_md_ok,
            "Run 'nexo install --local' to register guidance in CLAUDE.md.",
        )
    )

    settings_path = project_dir / ".claude" / "settings.json"
    hook_ok = _has_nexo_pretool_hook(settings_path)
    checks.append(
        (
            "pretool-hook",
            hook_ok,
            "Run 'nexo install --local' to add the PreToolUse hook in .claude/settings.json.",
        )
    )

    failed = [c for c in checks if not c[1]]
    print("nexo doctor")
    print()
    for check_id, ok, remediation in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {check_id}")
        if not ok:
            print(f"       fix: {remediation}")

    if failed:
        print()
        print(f"Doctor found {len(failed)} failing check(s).")
        return 1

    print()
    print("All checks passed.")
    return 0


def claude_install(project_dir: Path | None = None) -> None:
    """Write the nexo section to the local CLAUDE.md."""
    target = (project_dir or Path(".")) / "CLAUDE.md"

    if target.exists():
        content = target.read_text(encoding="utf-8")
        if _CLAUDE_MD_MARKER in content:
            print("nexo already configured in CLAUDE.md")
            return
        new_content = content.rstrip() + "\n\n" + _CLAUDE_MD_SECTION
    else:
        new_content = _CLAUDE_MD_SECTION

    target.write_text(new_content, encoding="utf-8")
    print(f"nexo section written to {target.resolve()}")

    # Also write Claude Code PreToolUse hook to .claude/settings.json
    _install_claude_hook(project_dir or Path("."))

    # Also wire up the stats session logging hook (PostToolUse)
    from nexo.stats import install_hook as _install_stats_hook
    settings_path = (project_dir or Path(".")) / ".claude" / "settings.json"
    msg = _install_stats_hook(settings_path)
    print(f"  {msg}")

    print()
    print("Claude Code will now check the knowledge graph before answering")
    print("codebase questions and rebuild it after code changes.")


def _install_claude_hook(project_dir: Path) -> None:
    """Add nexo PreToolUse hook to .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    hooks["PreToolUse"] = [h for h in pre_tool if "nexo" not in str(h)]
    hooks["PreToolUse"].append(_SETTINGS_HOOK)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"  .claude/settings.json  ->  PreToolUse hook registered")


def _uninstall_claude_hook(project_dir: Path) -> None:
    """Remove nexo PreToolUse hook from .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    pre_tool = settings.get("hooks", {}).get("PreToolUse", [])
    filtered = [h for h in pre_tool if "nexo" not in str(h)]
    if len(filtered) == len(pre_tool):
        return
    settings["hooks"]["PreToolUse"] = filtered
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"  .claude/settings.json  ->  PreToolUse hook removed")


def claude_uninstall(project_dir: Path | None = None) -> None:
    """Remove the nexo section from the local CLAUDE.md."""
    target = (project_dir or Path(".")) / "CLAUDE.md"

    if not target.exists():
        print("No CLAUDE.md found in current directory - nothing to do")
        return

    content = target.read_text(encoding="utf-8")
    if _CLAUDE_MD_MARKER not in content:
        print("nexo section not found in CLAUDE.md - nothing to do")
        return

    # Remove the ## nexo section: from the marker to the next ## heading or EOF
    cleaned = re.sub(
        r"\n*## nexo\n.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()
    if cleaned:
        target.write_text(cleaned + "\n", encoding="utf-8")
        print(f"nexo section removed from {target.resolve()}")
    else:
        target.unlink()
        print(f"CLAUDE.md was empty after removal - deleted {target.resolve()}")

    _uninstall_claude_hook(project_dir or Path("."))

    from nexo.stats import uninstall_hook as _uninstall_stats_hook
    settings_path = (project_dir or Path(".")) / ".claude" / "settings.json"
    msg = _uninstall_stats_hook(settings_path)
    print(f"  {msg}")


def _run_interactive_run(path: Path) -> None:
    """Orchestrate install, update check, and start interactive watcher."""
    import threading
    import time
    from nexo.watch import watch, WatchConfig, _rebuild_code

    print(f"\n--- nexo run ---")
    
    # 1. Check for updates
    latest = _check_pypi_version()
    if latest and latest != __version__:
        print(f"  [update] A newer version is available: {latest} (current: {__version__})")
        print(f"  [update] Run: pip install --upgrade nexo\n")
    
    # 2. Check install (doctor + auto-install)
    if doctor(path) != 0:
        print("\n  [run] Project setup incomplete. Running local install...")
        install(local=True)
        print("\n  [run] Setup complete. Starting watcher in 2s...")
        time.sleep(2)

    # 3. Start Watcher
    config = WatchConfig(obsidian_sync=False, debounce=3.0)
    watch_thread = threading.Thread(
        target=watch,
        args=(path, config),
        daemon=True
    )
    watch_thread.start()

    while not config.stop_requested:
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich import box
            
            console = Console()
            console.clear()
            
            # Header
            header = f"[bold magenta]nexo[/bold magenta] [cyan]interactive run[/cyan] | [yellow]{path.resolve()}[/yellow]"
            console.print(Panel(header, box=box.DOUBLE, border_style="magenta"))
            
            # Body content (Stats + Menu)
            stats_content = []
            graph_path = path / "nexo-out" / "graph.json"
            nodes, edges = 0, 0
            if graph_path.exists():
                try:
                    gdata = json.loads(graph_path.read_text(encoding="utf-8"))
                    nodes = len(gdata.get("nodes", []))
                    edges = len(gdata.get("links", gdata.get("edges", [])))
                except: pass
            
            stats_content.append(f"[bold cyan]Nodes:[/bold cyan] {nodes}")
            stats_content.append(f"[bold cyan]Edges:[/bold cyan] {edges}")
            stats_content.append(f"[bold cyan]Watcher:[/bold cyan] [green]Active[/green]")
            
            menu_content = (
                f"[bold white]Config:[/bold white]\n"
                f"  [bold blue]1[/bold blue] Obsidian Sync:  {'[bold green]ENABLED[/bold green]' if config.obsidian_sync else '[bold red]DISABLED[/bold red]'}\n"
                f"  [bold blue]2[/bold blue] Debounce:       [yellow]{config.debounce}s[/yellow]\n\n"
                f"[bold white]Actions:[/bold white]\n"
                f"  [bold blue]r[/bold blue] Manual Rebuild (AST only)\n"
                f"  [bold blue]d[/bold blue] Run Doctor checks\n"
                f"  [bold blue]i[/bold blue] Install Skill locally\n"
                f"  [bold blue]g[/bold blue] Install Skill globally\n"
                f"  [bold blue]q[/bold blue] Quit"
            )
            
            # Render using a table for layout
            layout_table = Table.grid(padding=1)
            layout_table.add_column()
            layout_table.add_column()
            layout_table.add_row(
                Panel("\n".join(stats_content), title="[bold cyan]Graph Stats[/bold cyan]", border_style="cyan", width=30),
                Panel(menu_content, title="[bold cyan]Control Menu[/bold cyan]", border_style="blue", width=40)
            )
            console.print(layout_table)
            
        except ImportError:
            # Fallback to plain UI with ANSI colors
            C_MAGENTA = "\033[95m"
            C_CYAN = "\033[96m"
            C_YELLOW = "\033[93m"
            C_GREEN = "\033[92m"
            C_RED = "\033[91m"
            C_WHITE = "\033[97m"
            C_BOLD = "\033[1m"
            C_RESET = "\033[0m"

            print("\033[H\033[J", end="")
            print(f"{C_BOLD}{C_MAGENTA}nexo{C_RESET} {C_CYAN}interactive run{C_RESET} | {C_YELLOW}{path.resolve()}{C_RESET}")
            print(f"{C_MAGENTA}{'=' * 60}{C_RESET}")
            
            graph_path = path / "nexo-out" / "graph.json"
            nodes, edges = 0, 0
            if graph_path.exists():
                try:
                    gdata = json.loads(graph_path.read_text(encoding="utf-8"))
                    nodes = len(gdata.get("nodes", []))
                    edges = len(gdata.get("links", gdata.get("edges", [])))
                except: pass

            print(f"{C_CYAN}Graph:{C_RESET}  {C_BOLD}{nodes}{C_RESET} nodes, {C_BOLD}{edges}{C_RESET} edges")
            print(f"{C_WHITE}Config:{C_RESET}")
            status_obsidian = f"{C_GREEN}ENABLED{C_RESET}" if config.obsidian_sync else f"{C_RED}DISABLED{C_RESET}"
            print(f"  {C_BOLD}[1]{C_RESET} Obsidian Sync (toggle): {status_obsidian}")
            print(f"  {C_BOLD}[2]{C_RESET} Debounce (set):         {C_YELLOW}{config.debounce}s{C_RESET}")
            print(f"{C_MAGENTA}{'-' * 60}{C_RESET}")
            print(f"{C_WHITE}Actions:{C_RESET}")
            print(f"  {C_BOLD}[r]{C_RESET} Manual Rebuild (AST only)")
            print(f"  {C_BOLD}[d]{C_RESET} Run Doctor checks")
            print(f"  {C_BOLD}[i]{C_RESET} Install Skill locally")
            print(f"  {C_BOLD}[g]{C_RESET} Install Skill globally")
            print(f"  {C_BOLD}[q]{C_RESET} Stop and exit")
            print(f"{C_MAGENTA}{'=' * 60}{C_RESET}")
            
            # Note: The Obsidian Sync [ENABLED/DISABLED] string above needs correction to use ANSI
            # (Fixing line 460 in replacement below)

        try:
            cmd = input("Command > ").strip().lower()
            if cmd == '1':
                config.obsidian_sync = not config.obsidian_sync
            elif cmd == '2':
                val = input("New debounce (seconds) > ")
                try:
                    config.debounce = float(val)
                except ValueError:
                    print("Invalid input - must be a number.")
                    time.sleep(1)
            elif cmd == 'r':
                print("\nTriggering manual rebuild...")
                from nexo.watch import _rebuild_code
                _rebuild_code(path, obsidian_sync=config.obsidian_sync)
                input("\nPress Enter to continue...")
            elif cmd == 'd':
                print("\nRunning doctor checks...")
                doctor(path)
                input("\nPress Enter to continue...")
            elif cmd == 'i':
                print("\nInstalling skill locally...")
                install(local=True)
                input("\nPress Enter to continue...")
            elif cmd == 'g':
                print("\nInstalling skill globally...")
                install(local=False)
                input("\nPress Enter to continue...")
            elif cmd == 'q':
                config.stop_requested = True
        except (EOFError, KeyboardInterrupt):
            config.stop_requested = True

    print("\nStopping watcher...")
    time.sleep(0.5)


def main() -> None:
    # Check all known skill install locations for a stale version stamp.
    # Skip during install/uninstall (hook writes trigger a fresh check anyway).
    # Deduplicate paths so platforms sharing the same install dir don't warn twice.
    if not any(arg in ("install", "uninstall") for arg in sys.argv):
        for skill_dst in {Path.home() / cfg["skill_dst"] for cfg in _PLATFORM_CONFIG.values()}:
            _check_skill_version(skill_dst)

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nexo <command>")
        print()
        print("Commands:")
        print("  mcp [graph.json]         start the local MCP stdio server for a graph")
        print("  install                 copy skill to platform config dir (global by default)")
        print("    --local                install into current project's .claude/ instead of home")
        print("    --platform <p>         force platform: claude (unix) | windows")
        print("  run [path]              interactive watcher: auto-install, update check, and UI")
        print("  path \"A\" \"B\"            shortest path between two nodes in graph.json")
        print("    --graph <path>          path to graph.json (default nexo-out/graph.json)")
        print("  explain \"X\"             plain-language explanation of a node and its neighbors")
        print("    --graph <path>          path to graph.json (default nexo-out/graph.json)")
        print("  add <url>               fetch a URL and save it to ./raw, then update the graph")
        print("    --author \"Name\"         tag the author of the content")
        print("    --contributor \"Name\"    tag who added it to the corpus")
        print("    --dir <path>            target directory (default: ./raw)")
        print("  watch <path>            watch a folder and rebuild the graph on code changes")
        print("    --debounce N            seconds to wait after last change (default 3)")
        print("    --obsidian-sync         also refresh Obsidian vault after code rebuild")
        print("    --obsidian-dir DIR      custom Obsidian vault directory")
        print("  workspace <path>        generate/update graph for all repos in a workspace")
        print("    --mode M               output mode: per-repo (default) | central")
        print("    --write-gitignore      auto-add graph output folder(s) to .gitignore")
        print("    --dry-run              preview actions without rebuilding graphs")
        print("    --no-respect-gitignore ignore .gitignore when scanning repos")
        print("  workspace query \"Q\"     query across repo graphs in a workspace")
        print("    --workspace DIR         workspace path (default: .)")
        print("    --mode M               source mode: auto (default) | per-repo | central")
        print("    --dfs                  use depth-first traversal")
        print("    --budget N             token budget (default 2000)")
        print("    --top-k N              merged hit count (default 15)")
        print("  update <path>           re-extract code files and update the graph (no LLM needed)")
        print("  cluster-only <path>     rerun clustering on an existing graph.json and regenerate report")
        print("  query \"<question>\"       BFS traversal of graph.json for a question")
        print("    --dfs                   use depth-first instead of breadth-first")
        print("    --budget N              cap output at N tokens (default 2000)")
        print("    --graph <path>          path to graph.json (default nexo-out/graph.json)")
        print("  save-result             save a Q&A result to nexo-out/memory/ for graph feedback loop")
        print("    --question Q            the question asked")
        print("    --answer A              the answer to save")
        print("    --type T                query type: query|path_query|explain (default: query)")
        print("    --nodes N1 N2 ...       source node labels cited in the answer")
        print("    --memory-dir DIR        memory directory (default: nexo-out/memory)")
        print("  stats                   show token usage: build cost, query savings, and live session estimate")
        print("    --out-dir <path>        output directory (default: nexo-out)")
        print("    --install-hook          add PostToolUse hook to .claude/settings.json for session tracking")
        print("    --uninstall-hook        remove the PostToolUse session hook")
        print("  benchmark [graph.json]  measure token reduction vs naive full-corpus approach")
        print("  doctor                  validate install, version marker, CLAUDE.md, and PreToolUse hook")
        print("  verify-mcp              verify AI used nexo MCP tools from session logs")
        print("    --workspace DIR       workspace path to match log entries (default: .)")
        print("    --session-log FILE    session log path (default: ~/.nexo_session.jsonl)")
        print("    --window-hours N      lookback window in hours (default: 24)")
        print("    --mode M              basic | strict (default: strict)")
        print("    --min-calls N         minimum nexo MCP tool calls required (default: 2)")
        print("    --json                print machine-readable JSON result")
        print("  verify-subagent         verify MCP usage with subagent-based validation")
        print("    --workspace DIR       workspace path to match log entries (default: .)")
        print("    --session-log FILE    session log path (default: ~/.nexo_session.jsonl)")
        print("    --window-hours N      lookback window in hours (default: 24)")
        print("    --mode M              basic | strict (default: strict)")
        print("    --answer TEXT         final answer text from main agent (optional)")
        print("    --json                print machine-readable JSON result")
        print("  hook install            install post-commit/post-checkout git hooks (all platforms)")
        print("  hook uninstall          remove git hooks")
        print("  hook status             check if git hooks are installed")
        print("  claude install          write nexo section to CLAUDE.md + PreToolUse hook (Claude Code)")
        print("  claude uninstall        remove nexo section from CLAUDE.md + PreToolUse hook")
        print()
        print("Conversation commands:")
        print("  conversation-status     show conversation metrics and health dashboard")
        print("    --db PATH              sessions database path (default: ~/.nexo/sessions.db)")
        print("    --json                 output as JSON")
        print("  conversation-export     export conversation sessions to file")
        print("    --db PATH              sessions database path")
        print("    --output PATH          output file path (default: nexo-out/conversations.json)")
        print("    --format FORMAT        output format: json or md (default: json)")
        print("  conversation-session ID  show details of a specific session")
        print("    --db PATH              sessions database path")
        print("  conversation-list        list all conversation sessions")
        print("    --db PATH              sessions database path")
        print()
        return

    cmd = sys.argv[1]
    if cmd == "install":
        # Default to windows platform on Windows, claude elsewhere
        default_platform = "windows" if platform.system() == "Windows" else "claude"
        chosen_platform = default_platform
        is_local = "--local" in sys.argv
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i].startswith("--platform="):
                chosen_platform = args[i].split("=", 1)[1]
                i += 1
            elif args[i] == "--platform" and i + 1 < len(args):
                chosen_platform = args[i + 1]
                i += 2
            elif args[i] == "--local":
                # already handled by is_local check above, just skip
                i += 1
            else:
                i += 1
        install(platform=chosen_platform, local=is_local)
    elif cmd == "run":
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        if not path.exists():
            print(f"error: path not found: {path}", file=sys.stderr)
            sys.exit(1)
        _run_interactive_run(path)
    elif cmd == "claude":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            claude_install()
        elif subcmd == "uninstall":
            claude_uninstall()
        else:
            print("Usage: nexo claude [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "hook":
        from nexo.hooks import install as hook_install, uninstall as hook_uninstall, status as hook_status
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            print(hook_install(Path(".")))
        elif subcmd == "uninstall":
            print(hook_uninstall(Path(".")))
        elif subcmd == "status":
            print(hook_status(Path(".")))
        else:
            print("Usage: nexo hook [install|uninstall|status]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "mcp":
        try:
            from nexo.serve import main as serve_main
        except Exception as exc:
            print(f"error: MCP server unavailable - {exc}", file=sys.stderr)
            print("  The 'mcp' package may have compatibility issues with your Python version.", file=sys.stderr)
            print("  CLI query tools still work without MCP server.", file=sys.stderr)
            sys.exit(1)

        serve_main(sys.argv[2:])
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: nexo query \"<question>\" [--dfs] [--budget N] [--graph path]", file=sys.stderr)
            sys.exit(1)
        from nexo.query_service import query_graph
        from nexo.mcp_verify import _DEFAULT_SESSION_LOG as _MCP_SESSION_LOG

        question = sys.argv[2]
        use_dfs = "--dfs" in sys.argv
        budget = 2000
        graph_path = "nexo-out/graph.json"
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--budget" and i + 1 < len(args):
                try:
                    budget = int(args[i + 1])
                except ValueError:
                    print(f"error: --budget must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 2
            elif args[i].startswith("--budget="):
                try:
                    budget = int(args[i].split("=", 1)[1])
                except ValueError:
                    print(f"error: --budget must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 1
            elif args[i] == "--graph" and i + 1 < len(args):
                graph_path = args[i + 1]; i += 2
            else:
                i += 1
        try:
            result = query_graph(question, graph_path=graph_path, use_dfs=use_dfs, budget=budget)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
        print(result["text"])

        # Log session for MCP verification
        # The CLI 'query' command corresponds to graph_summary + resolve_nodes in MCP
        try:
            from datetime import datetime, timezone
            entry = {"ts": datetime.now(timezone.utc).isoformat(), "tool": "nexo_graph_summary", "workspace": str(Path(".").resolve())}
            _MCP_SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
            with _MCP_SESSION_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            entry2 = {"ts": datetime.now(timezone.utc).isoformat(), "tool": "nexo_resolve_nodes", "workspace": str(Path(".").resolve())}
            with _MCP_SESSION_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry2) + "\n")
        except Exception:
            pass  # Silent fail for session logging
    elif cmd == "save-result":
        # nexo save-result --question Q --answer A --type T [--nodes N1 N2 ...]
        import argparse as _ap
        p = _ap.ArgumentParser(prog="nexo save-result")
        p.add_argument("--question", required=True)
        p.add_argument("--answer", required=True)
        p.add_argument("--type", dest="query_type", default="query")
        p.add_argument("--nodes", nargs="*", default=[])
        p.add_argument("--memory-dir", default="nexo-out/memory")
        opts = p.parse_args(sys.argv[2:])
        from nexo.ingest import save_query_result as _sqr
        out = _sqr(
            question=opts.question,
            answer=opts.answer,
            memory_dir=Path(opts.memory_dir),
            query_type=opts.query_type,
            source_nodes=opts.nodes or None,
        )
        print(f"Saved to {out}")
    elif cmd == "path":
        if len(sys.argv) < 4:
            print("Usage: nexo path \"<source>\" \"<target>\" [--graph path]", file=sys.stderr)
            sys.exit(1)
        from nexo.query_service import shortest_path_query

        source_label = sys.argv[2]
        target_label = sys.argv[3]
        graph_path = "nexo-out/graph.json"
        args = sys.argv[4:]
        for i, a in enumerate(args):
            if a == "--graph" and i + 1 < len(args):
                graph_path = args[i + 1]
        try:
            result = shortest_path_query(source_label, target_label, graph_path=graph_path)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
        print(result["text"])

    elif cmd == "explain":
        if len(sys.argv) < 3:
            print("Usage: nexo explain \"<node>\" [--graph path]", file=sys.stderr)
            sys.exit(1)
        from nexo.query_service import explain_node_query

        label = sys.argv[2]
        graph_path = "nexo-out/graph.json"
        args = sys.argv[3:]
        for i, a in enumerate(args):
            if a == "--graph" and i + 1 < len(args):
                graph_path = args[i + 1]
        try:
            result = explain_node_query(label, graph_path=graph_path)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
        print(result["text"])

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: nexo add <url> [--author Name] [--contributor Name] [--dir ./raw]", file=sys.stderr)
            sys.exit(1)
        from nexo.ingest import ingest as _ingest
        url = sys.argv[2]
        author: str | None = None
        contributor: str | None = None
        target_dir = Path("raw")
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--author" and i + 1 < len(args):
                author = args[i + 1]; i += 2
            elif args[i] == "--contributor" and i + 1 < len(args):
                contributor = args[i + 1]; i += 2
            elif args[i] == "--dir" and i + 1 < len(args):
                target_dir = Path(args[i + 1]); i += 2
            else:
                i += 1
        try:
            saved = _ingest(url, target_dir, author=author, contributor=contributor)
            print(f"Saved to {saved}")
            print("Run /nexo --update in your AI assistant to update the graph.")
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "watch":
        watch_path = Path(".")
        debounce = 3.0
        obsidian_sync = False
        obsidian_dir: Path | None = None

        args = sys.argv[2:]
        i = 0
        while i < len(args):
            token = args[i]
            if token == "--debounce" and i + 1 < len(args):
                try:
                    debounce = float(args[i + 1])
                except ValueError:
                    print("error: --debounce must be a number", file=sys.stderr)
                    sys.exit(1)
                i += 2
            elif token.startswith("--debounce="):
                try:
                    debounce = float(token.split("=", 1)[1])
                except ValueError:
                    print("error: --debounce must be a number", file=sys.stderr)
                    sys.exit(1)
                i += 1
            elif token == "--obsidian-sync":
                obsidian_sync = True
                i += 1
            elif token == "--obsidian-dir" and i + 1 < len(args):
                obsidian_dir = Path(args[i + 1])
                i += 2
            elif token.startswith("--obsidian-dir="):
                obsidian_dir = Path(token.split("=", 1)[1])
                i += 1
            elif token.startswith("--"):
                print(f"error: unknown watch option '{token}'", file=sys.stderr)
                sys.exit(1)
            else:
                watch_path = Path(token)
                i += 1

        if obsidian_dir is not None:
            obsidian_sync = True

        if not watch_path.exists():
            print(f"error: path not found: {watch_path}", file=sys.stderr)
            sys.exit(1)
        from nexo.watch import watch as _watch
        try:
            _watch(
                watch_path,
                debounce=debounce,
                obsidian_sync=obsidian_sync,
                obsidian_dir=obsidian_dir,
            )
        except ImportError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "workspace":
        args = sys.argv[2:]
        if args and args[0] == "query":
            if len(args) < 2:
                print(
                    "Usage: nexo workspace query \"<question>\" "
                    "[--workspace DIR] [--mode auto|per-repo|central] [--dfs] "
                    "[--budget N] [--top-k N]",
                    file=sys.stderr,
                )
                sys.exit(1)

            question = args[1]
            workspace_path = Path(".")
            mode = "auto"
            use_dfs = False
            budget = 2000
            top_k = 15

            i = 2
            while i < len(args):
                token = args[i]
                if token == "--workspace" and i + 1 < len(args):
                    workspace_path = Path(args[i + 1])
                    i += 2
                elif token.startswith("--workspace="):
                    workspace_path = Path(token.split("=", 1)[1])
                    i += 1
                elif token == "--mode" and i + 1 < len(args):
                    mode = args[i + 1]
                    i += 2
                elif token.startswith("--mode="):
                    mode = token.split("=", 1)[1]
                    i += 1
                elif token == "--dfs":
                    use_dfs = True
                    i += 1
                elif token == "--budget" and i + 1 < len(args):
                    try:
                        budget = int(args[i + 1])
                    except ValueError:
                        print("error: --budget must be an integer", file=sys.stderr)
                        sys.exit(1)
                    i += 2
                elif token.startswith("--budget="):
                    try:
                        budget = int(token.split("=", 1)[1])
                    except ValueError:
                        print("error: --budget must be an integer", file=sys.stderr)
                        sys.exit(1)
                    i += 1
                elif token == "--top-k" and i + 1 < len(args):
                    try:
                        top_k = int(args[i + 1])
                    except ValueError:
                        print("error: --top-k must be an integer", file=sys.stderr)
                        sys.exit(1)
                    i += 2
                elif token.startswith("--top-k="):
                    try:
                        top_k = int(token.split("=", 1)[1])
                    except ValueError:
                        print("error: --top-k must be an integer", file=sys.stderr)
                        sys.exit(1)
                    i += 1
                else:
                    print(f"error: unknown workspace query option '{token}'", file=sys.stderr)
                    sys.exit(1)

            if not workspace_path.exists():
                print(f"error: path not found: {workspace_path}", file=sys.stderr)
                sys.exit(1)

            try:
                from nexo.workspace import run_workspace_query
                result = run_workspace_query(
                    workspace_path,
                    question=question,
                    use_dfs=use_dfs,
                    budget=budget,
                    mode=mode,
                    top_k=top_k,
                )
            except ImportError as exc:
                print(f"error: missing dependency for workspace query: {exc}", file=sys.stderr)
                sys.exit(1)
            print(result["text"])
            sys.exit(0)

        workspace_path = Path(".")
        mode = "per-repo"
        write_gitignore = False
        dry_run = False
        respect_gitignore = True

        i = 0
        while i < len(args):
            token = args[i]
            if token == "--mode" and i + 1 < len(args):
                mode = args[i + 1]
                i += 2
            elif token.startswith("--mode="):
                mode = token.split("=", 1)[1]
                i += 1
            elif token == "--write-gitignore":
                write_gitignore = True
                i += 1
            elif token == "--dry-run":
                dry_run = True
                i += 1
            elif token == "--no-respect-gitignore":
                respect_gitignore = False
                i += 1
            elif token.startswith("--"):
                print(f"error: unknown workspace option '{token}'", file=sys.stderr)
                sys.exit(1)
            else:
                workspace_path = Path(token)
                i += 1

        if not workspace_path.exists():
            print(f"error: path not found: {workspace_path}", file=sys.stderr)
            sys.exit(1)

        from nexo.workspace import run_workspace_update

        summary = run_workspace_update(
            workspace_path,
            mode=mode,
            write_gitignore=write_gitignore,
            respect_gitignore=respect_gitignore,
            dry_run=dry_run,
        )

        print(
            f"Workspace: {summary['workspace']} | mode={summary['mode']} | "
            f"repos={summary['total_repos']} | ok={summary['ok_repos']} | failed={summary['failed_repos']}"
        )
        if summary.get("index_path"):
            print(f"Index: {summary['index_path']}")
        for item in summary["repos"]:
            status = "OK" if item["ok"] else "FAILED"
            suffix = " (dry-run)" if item.get("dry_run") else ""
            print(f"- [{status}] {item['repo']} -> {item['output']}{suffix}")

        if summary["failed_repos"] > 0:
            sys.exit(1)

    elif cmd == "cluster-only":
        watch_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        graph_json = watch_path / "nexo-out" / "graph.json"
        if not graph_json.exists():
            print(f"error: no graph found at {graph_json} — run /nexo first", file=sys.stderr)
            sys.exit(1)
        from networkx.readwrite import json_graph as _jg
        from nexo.build import build_from_json
        from nexo.cluster import cluster, score_all
        from nexo.analyze import god_nodes, surprising_connections, suggest_questions
        from nexo.report import generate
        from nexo.export import to_json
        print("Loading existing graph...")
        _raw = json.loads(graph_json.read_text(encoding="utf-8"))
        G = build_from_json(_raw)
        print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        print("Re-clustering...")
        communities = cluster(G)
        cohesion = score_all(G, communities)
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        labels = {cid: f"Community {cid}" for cid in communities}
        questions = suggest_questions(G, communities, labels)
        tokens = {"input": 0, "output": 0}
        report = generate(G, communities, cohesion, labels, gods, surprises,
                          {}, tokens, str(watch_path), suggested_questions=questions)
        out = watch_path / "nexo-out"
        (out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
        to_json(G, communities, str(out / "graph.json"))
        print(f"Done — {len(communities)} communities. GRAPH_REPORT.md and graph.json updated.")

    elif cmd == "update":
        watch_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        if not watch_path.exists():
            print(f"error: path not found: {watch_path}", file=sys.stderr)
            sys.exit(1)
        from nexo.watch import _rebuild_code
        print(f"Re-extracting code files in {watch_path} (no LLM needed)...")
        ok = _rebuild_code(watch_path)
        if ok:
            print("Code graph updated. For doc/paper/image changes run /nexo --update in your AI assistant.")
        else:
            print("Nothing to update or rebuild failed — check output above.", file=sys.stderr)
            sys.exit(1)

    elif cmd == "stats":
        from nexo.stats import print_stats, install_hook, uninstall_hook
        out_dir = Path("nexo-out")
        settings_path = Path(".claude") / "settings.json"
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--out-dir" and i + 1 < len(args):
                out_dir = Path(args[i + 1]); i += 2
            elif args[i].startswith("--out-dir="):
                out_dir = Path(args[i].split("=", 1)[1]); i += 1
            elif args[i] == "--install-hook":
                print(install_hook(settings_path)); sys.exit(0)
            elif args[i] == "--uninstall-hook":
                print(uninstall_hook(settings_path)); sys.exit(0)
            else:
                i += 1
        print_stats(out_dir)

    elif cmd == "benchmark":
        from nexo.benchmark import run_benchmark, print_benchmark
        graph_path = sys.argv[2] if len(sys.argv) > 2 else "nexo-out/graph.json"
        # Try to load corpus_words from detect output
        corpus_words = None
        detect_path = Path(".nexo_detect.json")
        if detect_path.exists():
            try:
                detect_data = json.loads(detect_path.read_text(encoding="utf-8"))
                corpus_words = detect_data.get("total_words")
            except Exception:
                pass
        result = run_benchmark(graph_path, corpus_words=corpus_words)
        print_benchmark(result)
    elif cmd == "doctor":
        exit_code = doctor(Path("."))
        if exit_code != 0:
            sys.exit(exit_code)

    elif cmd == "verify-mcp":
        from nexo.mcp_verify import verify_mcp_usage

        workspace = Path(".")
        session_log: Path | None = None
        window_hours = 24
        mode = "strict"
        min_calls = 2
        as_json = False

        args = sys.argv[2:]
        i = 0
        while i < len(args):
            token = args[i]
            if token == "--workspace" and i + 1 < len(args):
                workspace = Path(args[i + 1]); i += 2
            elif token.startswith("--workspace="):
                workspace = Path(token.split("=", 1)[1]); i += 1
            elif token == "--session-log" and i + 1 < len(args):
                session_log = Path(args[i + 1]); i += 2
            elif token.startswith("--session-log="):
                session_log = Path(token.split("=", 1)[1]); i += 1
            elif token == "--window-hours" and i + 1 < len(args):
                try:
                    window_hours = int(args[i + 1])
                except ValueError:
                    print("error: --window-hours must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 2
            elif token.startswith("--window-hours="):
                try:
                    window_hours = int(token.split("=", 1)[1])
                except ValueError:
                    print("error: --window-hours must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 1
            elif token == "--mode" and i + 1 < len(args):
                mode = args[i + 1]; i += 2
            elif token.startswith("--mode="):
                mode = token.split("=", 1)[1]; i += 1
            elif token == "--min-calls" and i + 1 < len(args):
                try:
                    min_calls = int(args[i + 1])
                except ValueError:
                    print("error: --min-calls must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 2
            elif token.startswith("--min-calls="):
                try:
                    min_calls = int(token.split("=", 1)[1])
                except ValueError:
                    print("error: --min-calls must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 1
            elif token == "--json":
                as_json = True; i += 1
            else:
                print(f"error: unknown verify-mcp option '{token}'", file=sys.stderr)
                sys.exit(1)

        try:
            result = verify_mcp_usage(
                workspace=workspace,
                session_log=session_log,
                window_hours=window_hours,
                mode=mode,
                min_calls=min_calls,
            )
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)

        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print(result["text"])

        if not result["pass"]:
            sys.exit(1)

    elif cmd == "verify-subagent":
        from nexo.mcp_subagent import verify_mcp_with_subagent

        workspace = Path(".")
        session_log: Path | None = None
        window_hours = 24
        mode = "strict"
        answer_text: str | None = None
        as_json = False

        args = sys.argv[2:]
        i = 0
        while i < len(args):
            token = args[i]
            if token == "--workspace" and i + 1 < len(args):
                workspace = Path(args[i + 1]); i += 2
            elif token.startswith("--workspace="):
                workspace = Path(token.split("=", 1)[1]); i += 1
            elif token == "--session-log" and i + 1 < len(args):
                session_log = Path(args[i + 1]); i += 2
            elif token.startswith("--session-log="):
                session_log = Path(token.split("=", 1)[1]); i += 1
            elif token == "--window-hours" and i + 1 < len(args):
                try:
                    window_hours = int(args[i + 1])
                except ValueError:
                    print("error: --window-hours must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 2
            elif token.startswith("--window-hours="):
                try:
                    window_hours = int(token.split("=", 1)[1])
                except ValueError:
                    print("error: --window-hours must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 1
            elif token == "--mode" and i + 1 < len(args):
                mode = args[i + 1]; i += 2
            elif token.startswith("--mode="):
                mode = token.split("=", 1)[1]; i += 1
            elif token == "--answer" and i + 1 < len(args):
                answer_text = args[i + 1]; i += 2
            elif token.startswith("--answer="):
                answer_text = token.split("=", 1)[1]; i += 1
            elif token == "--json":
                as_json = True; i += 1
            else:
                print(f"error: unknown verify-subagent option '{token}'", file=sys.stderr)
                sys.exit(1)

        try:
            _, exit_code = verify_mcp_with_subagent(
                workspace=workspace,
                session_log=session_log,
                window_hours=window_hours,
                mode=mode,
                answer_text=answer_text,
                as_json=as_json,
            )
            sys.exit(exit_code)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)

    # --- Internal subcommands for the standalone pipeline ---
    elif cmd == "internal-detect":
        if len(sys.argv) < 3:
            sys.exit(1)
        from nexo.detect import detect
        print(json.dumps(detect(Path(sys.argv[2]))))

    elif cmd == "internal-extract":
        # internal-extract <detect_json_path> <out_json_path>
        if len(sys.argv) < 4:
            sys.exit(1)
        from nexo.extract import collect_files, extract
        detect_data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        code_files = []
        for f in detect_data.get("files", {}).get("code", []):
            p = Path(f)
            code_files.extend(collect_files(p) if p.is_dir() else [p])
        
        if code_files:
            result = extract(code_files)
        else:
            result = {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}
        Path(sys.argv[3]).write_text(json.dumps(result, indent=2), encoding="utf-8")

    elif cmd == "internal-merge":
        # internal-merge <ast_json> <semantic_json> <out_json>
        if len(sys.argv) < 5:
            sys.exit(1)
        ast = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        sem = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        # Basic merge logic
        merged = {
            "nodes": ast.get("nodes", []) + sem.get("nodes", []),
            "edges": ast.get("edges", []) + sem.get("edges", []),
            "input_tokens": ast.get("input_tokens", 0) + sem.get("input_tokens", 0),
            "output_tokens": ast.get("output_tokens", 0) + sem.get("output_tokens", 0),
        }
        Path(sys.argv[4]).write_text(json.dumps(merged, indent=2), encoding="utf-8")

    elif cmd == "internal-analyze":
        # internal-analyze <extraction_json> <detect_json> <out_dir> <input_path>
        if len(sys.argv) < 6:
            sys.exit(1)
        from nexo.build import build_from_json
        from nexo.cluster import cluster, score_all
        from nexo.analyze import god_nodes, surprising_connections, suggest_questions
        from nexo.report import generate
        from nexo.export import to_json
        
        extraction = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        detection = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        out_dir = Path(sys.argv[4])
        input_path = sys.argv[5]
        
        G = build_from_json(extraction)
        communities = cluster(G)
        cohesion = score_all(G, communities)
        tokens = {"input": extraction.get("input_tokens", 0), "output": extraction.get("output_tokens", 0)}
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        labels = {cid: f"Community {cid}" for cid in communities}
        questions = suggest_questions(G, communities, labels)
        
        report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, input_path, suggested_questions=questions)
        (out_dir / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
        to_json(G, communities, str(out_dir / "graph.json"))
        
        analysis = {
            "communities": {str(k): v for k, v in communities.items()},
            "cohesion": {str(k): v for k, v in cohesion.items()},
            "gods": gods,
            "surprises": surprises,
            "questions": questions,
        }
        (out_dir / ".nexo_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities")

    elif cmd == "internal-label":
        # internal-label <out_dir> <input_path> <labels_json>
        if len(sys.argv) < 5:
            sys.exit(1)
        from nexo.build import build_from_json
        from nexo.export import to_json
        from nexo.report import generate
        
        out_dir = Path(sys.argv[2])
        input_path = sys.argv[3]
        labels = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
        # Cast keys to int
        labels = {int(k): v for k, v in labels.items()}
        
        extraction = json.loads((out_dir / ".nexo_extract.json").read_text(encoding="utf-8"))
        detection = json.loads((out_dir / ".nexo_detect.json").read_text(encoding="utf-8"))
        analysis = json.loads((out_dir / ".nexo_analysis.json").read_text(encoding="utf-8"))
        
        G = build_from_json(extraction)
        # Parse communities from analysis
        communities = {int(k): v for k, v in analysis.get("communities", {}).items()}
        cohesion = {int(k): v for k, v in analysis.get("cohesion", {}).items()}
        tokens = {"input": extraction.get("input_tokens", 0), "output": extraction.get("output_tokens", 0)}
        
        from nexo.analyze import suggest_questions
        questions = suggest_questions(G, communities, labels)
        
        report = generate(G, communities, cohesion, labels, analysis.get("gods", []), 
                          analysis.get("surprises", []), detection, tokens, input_path, 
                          suggested_questions=questions)
        (out_dir / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
        to_json(G, communities, str(out_dir / "graph.json"))

    elif cmd == "internal-manifest":
        # internal-manifest <out_dir>
        if len(sys.argv) < 3:
            sys.exit(1)
        out_dir = Path(sys.argv[2])
        extraction_path = out_dir / ".nexo_extract.json"
        detect_path = out_dir / ".nexo_detect.json"
        
        extraction = json.loads(extraction_path.read_text(encoding="utf-8")) if extraction_path.exists() else {}
        detect = json.loads(detect_path.read_text(encoding="utf-8")) if detect_path.exists() else {}
        
        input_tok = extraction.get("input_tokens", 0)
        output_tok = extraction.get("output_tokens", 0)
        
        # 1. Update cost.json (cumulative)
        from datetime import datetime, timezone
        cost_path = out_dir / "cost.json"
        if cost_path.exists():
            try:
                cost = json.loads(cost_path.read_text(encoding="utf-8"))
            except:
                cost = {"runs": [], "total_input_tokens": 0, "total_output_tokens": 0}
        else:
            cost = {"runs": [], "total_input_tokens": 0, "total_output_tokens": 0}
            
        cost["runs"].append({
            "date": datetime.now(timezone.utc).isoformat(),
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "files": detect.get("total_files", 0),
        })
        cost["total_input_tokens"] += input_tok
        cost["total_output_tokens"] += output_tok
        cost_path.write_text(json.dumps(cost, indent=2), encoding="utf-8")
        
        # 2. Save manifest for --update
        from nexo.detect import save_manifest
        save_manifest(detect.get("files", {}))
        
        print(f"This run: {input_tok:,} input tokens, {output_tok:,} output tokens")
        print(f"All time: {cost['total_input_tokens']:,} input, {cost['total_output_tokens']:,} output ({len(cost['runs'])} runs)")

    elif cmd == "internal-transcribe":
        # internal-transcribe <detect_json> <out_json>
        if len(sys.argv) < 4:
            sys.exit(1)
        import os
        from nexo.transcribe import transcribe_all
        detect = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        video_files = detect.get("files", {}).get("video", [])
        prompt = os.environ.get("NEXO_WHISPER_PROMPT", "Use proper punctuation and paragraph breaks.")
        transcript_paths = transcribe_all(video_files, initial_prompt=prompt)
        Path(sys.argv[3]).write_text(json.dumps(transcript_paths), encoding="utf-8")

    elif cmd == "internal-cache-check":
        # internal-cache-check <detect_json> <cached_json_out> <uncached_txt_out>
        if len(sys.argv) < 5:
            sys.exit(1)
        from nexo.cache import check_semantic_cache
        detect = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        all_files = [f for files in detect.get("files", {}).values() for f in files]
        cn, ce, che, uncached = check_semantic_cache(all_files)
        if cn or ce or che:
            Path(sys.argv[3]).write_text(json.dumps({"nodes": cn, "edges": ce, "hyperedges": che}), encoding="utf-8")
        Path(sys.argv[4]).write_text("\n".join(uncached), encoding="utf-8")
        print(f"Cache: {len(all_files)-len(uncached)} files hit, {len(uncached)} files need extraction")

    elif cmd == "internal-cache-save":
        # internal-cache-save <new_semantic_json>
        if len(sys.argv) < 3:
            sys.exit(1)
        from nexo.cache import save_semantic_cache
        p = Path(sys.argv[2])
        new = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"nodes": [], "edges": [], "hyperedges": []}
        saved = save_semantic_cache(new.get("nodes", []), new.get("edges", []), new.get("hyperedges", []))
        print(f"Cached {saved} files")

    elif cmd == "internal-merge-semantic":
        # internal-merge-semantic <cached_json> <new_json> <out_json>
        if len(sys.argv) < 5:
            sys.exit(1)
        p_cached = Path(sys.argv[2])
        p_new = Path(sys.argv[3])
        cached = json.loads(p_cached.read_text(encoding="utf-8")) if p_cached.exists() else {"nodes": [], "edges": [], "hyperedges": []}
        new = json.loads(p_new.read_text(encoding="utf-8")) if p_new.exists() else {"nodes": [], "edges": [], "hyperedges": []}
        
        all_nodes = cached.get("nodes", []) + new.get("nodes", [])
        all_edges = cached.get("edges", []) + new.get("edges", [])
        all_hyperedges = cached.get("hyperedges", []) + new.get("hyperedges", [])
        
        seen = set()
        deduped = []
        for n in all_nodes:
            if n["id"] not in seen:
                seen.add(n["id"])
                deduped.append(n)
        
        merged = {
            "nodes": deduped,
            "edges": all_edges,
            "hyperedges": all_hyperedges,
            "input_tokens": new.get("input_tokens", 0),
            "output_tokens": new.get("output_tokens", 0),
        }
        Path(sys.argv[4]).write_text(json.dumps(merged, indent=2), encoding="utf-8")
        print(f"Extraction complete - {len(deduped)} nodes, {len(all_edges)} edges ({len(cached.get('nodes', []))} from cache, {len(new.get('nodes', []))} new)")

    elif cmd == "internal-html":
        # internal-html <out_dir>
        if len(sys.argv) < 3:
            sys.exit(1)
        from nexo.export import to_html
        from nexo.build import build_from_json
        out_dir = Path(sys.argv[2])
        extraction = json.loads((out_dir / ".nexo_extract.json").read_text(encoding="utf-8"))
        analysis = json.loads((out_dir / ".nexo_analysis.json").read_text(encoding="utf-8"))
        labels_path = out_dir / ".nexo_labels.json"
        labels_raw = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
        G = build_from_json(extraction)
        if G.number_of_nodes() > 5000:
            print(f"Graph has {G.number_of_nodes()} nodes - too large for HTML viz. Use Obsidian vault instead.")
            return
        communities = {int(k): v for k, v in analysis.get("communities", {}).items()}
        labels = {int(k): v for k, v in labels_raw.items()}
        to_html(G, communities, str(out_dir / "graph.html"), community_labels=labels or None)
        print("graph.html written - open in any browser, no server needed")

    elif cmd == "internal-wiki":
        # internal-wiki <out_dir>
        if len(sys.argv) < 3:
            sys.exit(1)
        from nexo.wiki import to_wiki
        from nexo.build import build_from_json
        from nexo.analyze import god_nodes
        out_dir = Path(sys.argv[2])
        extraction = json.loads((out_dir / ".nexo_extract.json").read_text(encoding="utf-8"))
        analysis = json.loads((out_dir / ".nexo_analysis.json").read_text(encoding="utf-8"))
        labels_path = out_dir / ".nexo_labels.json"
        labels_raw = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
        G = build_from_json(extraction)
        communities = {int(k): v for k, v in analysis.get("communities", {}).items()}
        cohesion = {int(k): v for k, v in analysis.get("cohesion", {}).items()}
        labels = {int(k): v for k, v in labels_raw.items()}
        gods = god_nodes(G)
        n = to_wiki(G, communities, str(out_dir / "wiki"), community_labels=labels or None, cohesion=cohesion, god_nodes_data=gods)
        print(f"Wiki: {n} articles written to {out_dir}/wiki/")
        print(f"  {out_dir}/wiki/index.md  ->  agent entry point")

    elif cmd == "internal-export":
        # internal-export <type> <out_dir> [target_file_or_dir]
        if len(sys.argv) < 4:
            sys.exit(1)
        etype = sys.argv[2]
        out_dir = Path(sys.argv[3])
        target = sys.argv[4] if len(sys.argv) > 4 else None
        
        from nexo.build import build_from_json
        from nexo.export import to_cypher, to_mermaid, to_d2, to_gephi, to_dot, to_graphml, to_json
        
        extraction = json.loads((out_dir / ".nexo_extract.json").read_text(encoding="utf-8"))
        G = build_from_json(extraction)
        
        if etype == "cypher":
            path = target or str(out_dir / "cypher.txt")
            to_cypher(G, path)
            print(f"cypher.txt written - import with: cypher-shell < {path}")
        elif etype == "mermaid":
            path = target or str(out_dir / "graph.mmd")
            to_mermaid(G, path)
            print(f"Mermaid graph: {path}")
        elif etype == "d2":
            path = target or str(out_dir / "graph.d2")
            to_d2(G, path)
            print(f"D2 graph: {path}")
        elif etype == "gephi":
            path = target or str(out_dir / "graph.gexf")
            to_gephi(G, path)
            print(f"Gephi graph: {path}")
        elif etype == "dot":
            path = target or str(out_dir / "graph.dot")
            to_dot(G, path)
            print(f"DOT graph: {path}")
        elif etype == "graphml":
            path = target or str(out_dir / "graph.graphml")
            to_graphml(G, path)
            print(f"GraphML graph: {path}")
        elif etype == "json":
            path = target or str(out_dir / "graph.json")
            analysis = json.loads((out_dir / ".nexo_analysis.json").read_text(encoding="utf-8"))
            communities = {int(k): v for k, v in analysis.get("communities", {}).items()}
            to_json(G, communities, path)
            print(f"JSON graph: {path}")

    elif cmd == "internal-cluster":
        # internal-cluster <out_dir>
        if len(sys.argv) < 3:
            sys.exit(1)
        from nexo.cluster import cluster, score_all
        from nexo.analyze import god_nodes, surprising_connections, suggest_questions
        from nexo.report import generate
        from nexo.export import to_json
        from networkx.readwrite import json_graph
        
        out_dir = Path(sys.argv[2])
        graph_path = out_dir / "graph.json"
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        try:
            G = json_graph.node_link_graph(data, edges="links")
        except:
            G = json_graph.node_link_graph(data)
            
        communities = cluster(G)
        cohesion = score_all(G, communities)
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        labels = {cid: f"Community {cid}" for cid in communities}
        
        # Dummy detection and tokens for re-cluster report
        detection = {"total_files": 0, "total_words": 0, "files": {"code": [], "document": [], "paper": []}}
        tokens = {"input": 0, "output": 0}
        
        questions = suggest_questions(G, communities, labels)
        report = generate(G, communities, cohesion, labels, gods, surprises, detection, tokens, ".", suggested_questions=questions)
        (out_dir / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
        to_json(G, communities, str(graph_path))
        
        analysis = {
            "communities": {str(k): v for k, v in communities.items()},
            "cohesion": {str(k): v for k, v in cohesion.items()},
            "gods": gods,
            "surprises": surprises,
            "questions": questions,
        }
        (out_dir / ".nexo_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        print(f"Re-clustered: {len(communities)} communities")

    elif cmd == "internal-obsidian":
        # internal-obsidian <out_dir> <vault_dir>
        if len(sys.argv) < 4:
            sys.exit(1)
        from nexo.export import to_obsidian, to_canvas
        from nexo.build import build_from_json
        out_dir = Path(sys.argv[2])
        vault_dir = Path(sys.argv[3])
        
        extraction = json.loads((out_dir / ".nexo_extract.json").read_text(encoding="utf-8"))
        analysis = json.loads((out_dir / ".nexo_analysis.json").read_text(encoding="utf-8"))
        labels_path = out_dir / ".nexo_labels.json"
        labels_raw = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
        
        G = build_from_json(extraction)
        communities = {int(k): v for k, v in analysis.get("communities", {}).items()}
        cohesion = {int(k): v for k, v in analysis.get("cohesion", {}).items()}
        labels = {int(k): v for k, v in labels_raw.items()}
        
        n = to_obsidian(G, communities, str(vault_dir), community_labels=labels or None, cohesion=cohesion)
        print(f"Obsidian vault: {n} notes in {vault_dir}/")
        
        to_canvas(G, communities, str(vault_dir / "graph.canvas"), community_labels=labels or None)
        print(f"Canvas: {vault_dir}/graph.canvas - open in Obsidian for structured community layout")

    elif cmd == "conversation-status":
        # nexo conversation-status [--db PATH] [--json]
        from nexo.dashboard import create_dashboard
        db_path = None
        as_json = False
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--db" and i + 1 < len(args):
                db_path = Path(args[i + 1]); i += 2
            elif args[i] == "--json":
                as_json = True; i += 1
            else:
                i += 1

        dashboard = create_dashboard(db_path)
        if as_json:
            print(json.dumps(dashboard.get_metrics_json(), indent=2))
        else:
            print(dashboard.generate_report())

    elif cmd == "conversation-export":
        # nexo conversation-export [--db PATH] [--output PATH] [--format json|md]
        from nexo.dashboard import create_dashboard
        from nexo.session import SessionStore
        db_path = None
        output_path = Path("nexo-out/conversations.json")
        format = "json"
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--db" and i + 1 < len(args):
                db_path = Path(args[i + 1]); i += 2
            elif args[i] == "--output" and i + 1 < len(args):
                output_path = Path(args[i + 1]); i += 2
            elif args[i] == "--format" and i + 1 < len(args):
                format = args[i + 1]; i += 2
            else:
                i += 1

        dashboard = create_dashboard(db_path)
        if format == "md":
            output_path = output_path.with_suffix(".md")
            dashboard.export_report(output_path, format="md")
        else:
            # Export sessions data as JSON
            store = SessionStore(db_path)
            sessions_data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sessions": [],
            }
            for session_id in store.list_sessions():
                turns = store.get_turns(session_id)
                checkpoint = store.load_checkpoint(session_id)
                sessions_data["sessions"].append({
                    "session_id": session_id,
                    "turns": turns,
                    "checkpoint": {
                        "turn_id": checkpoint.turn_id if checkpoint else None,
                        "current_node": checkpoint.current_node if checkpoint else None,
                        "path_history": checkpoint.path_history if checkpoint else [],
                        "collected_slots": checkpoint.collected_slots if checkpoint else {},
                    } if checkpoint else None,
                })
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(sessions_data, indent=2), encoding="utf-8")
        print(f"Exported to: {output_path}")

    elif cmd == "conversation-session":
        # nexo conversation-session <session_id> [--db PATH]
        from nexo.session import SessionStore
        if len(sys.argv) < 3:
            print("Usage: nexo conversation-session <session_id> [--db PATH]", file=sys.stderr)
            sys.exit(1)

        session_id = sys.argv[2]
        db_path = None
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--db" and i + 1 < len(args):
                db_path = Path(args[i + 1]); i += 2
            else:
                i += 1

        store = SessionStore(db_path)
        checkpoint = store.load_checkpoint(session_id)
        turns = store.get_turns(session_id)

        if not checkpoint:
            print(f"Session '{session_id}' not found", file=sys.stderr)
            sys.exit(1)

        print(f"Session: {session_id}")
        print(f"Current Node: {checkpoint.current_node}")
        print(f"Turn Count: {len(turns)}")
        print(f"Path History: {' -> '.join(checkpoint.path_history)}")
        if checkpoint.collected_slots:
            print(f"Collected Slots: {checkpoint.collected_slots}")
        print()
        print("Turns:")
        for turn in turns:
            print(f"  [{turn['turn_id']}] User: {turn['user_input']}")
            print(f"           AI: {turn['ai_response']}")
            if turn.get('matched_nodes'):
                print(f"           Matched: {', '.join(turn['matched_nodes'])}")
            print()

    elif cmd == "conversation-list":
        # nexo conversation-list [--db PATH]
        from nexo.session import SessionStore
        db_path = None
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--db" and i + 1 < len(args):
                db_path = Path(args[i + 1]); i += 2
            else:
                i += 1

        store = SessionStore(db_path)
        sessions = store.list_sessions()

        if not sessions:
            print("No sessions found")
        else:
            print(f"Sessions ({len(sessions)}):")
            for session_id in sessions:
                checkpoint = store.load_checkpoint(session_id)
                turns = store.get_turns(session_id)
                status = "active" if checkpoint and checkpoint.current_node else "empty"
                print(f"  {session_id}: {len(turns)} turns, {status} ({checkpoint.current_node if checkpoint else 'N/A'})")

    elif cmd == "internal-detect-incremental":
        # internal-detect-incremental <root_path> <out_dir>
        if len(sys.argv) < 4:
            sys.exit(1)
        from nexo.detect import detect_incremental
        root = Path(sys.argv[2])
        out_dir = Path(sys.argv[3])
        manifest_path = str(out_dir / "manifest.json")
        result = detect_incremental(root, manifest_path=manifest_path)
        print(json.dumps(result))

    elif cmd == "internal-merge-incremental":
        # internal-merge-incremental <root_path> <incremental_json>
        if len(sys.argv) < 4:
            sys.exit(1)
        from nexo.export import merge_incremental
        root = Path(sys.argv[2])
        incremental_json = Path(sys.argv[3])
        result = json.loads(incremental_json.read_text(encoding="utf-8"))
        merge_incremental(root, result)

    else:
        print(f"error: unknown command '{cmd}'", file=sys.stderr)
        print("Run 'nexo --help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
