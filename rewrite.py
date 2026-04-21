import re
from pathlib import Path

f = Path("nexo/__main__.py")
if f.exists():
    lines = f.read_text("utf-8").splitlines()
    
    # 1. Simplify _PLATFORM_CONFIG
    in_platform_config = False
    in_install = False
    
    new_lines = []
    skip = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Strip _AGENTS_MD_SECTION to _agents_uninstall
        if "_AGENTS_MD_SECTION =" in line:
            # We skip until we hit def claude_install
            while i < len(lines) and not lines[i].startswith("def claude_install("):
                i += 1
            continue

        # In _PLATFORM_CONFIG
        if line.startswith("_PLATFORM_CONFIG: dict[str, dict] = {"):
            new_lines.append(line)
            # Keep until we reach claude
            i += 1
            while i < len(lines) and line != "}":
                line = lines[i]
                if '"claude": {' in line or '"windows": {' in line:
                    # Append the block
                    new_lines.append(line)
                    i += 1
                    while i < len(lines) and not lines[i].strip() == "},":
                        new_lines.append(lines[i])
                        i += 1
                    new_lines.append(lines[i]) # "},"
                elif line == "}":
                    new_lines.append(line)
                i += 1
            continue

        # In install()
        if line.startswith("def install(platform: str = "):
            new_lines.append(line)
            i += 1
            while i < len(lines) and lines[i].startswith("    if platform == \"gemini\""):
                # skip gemini and cursor blocks
                i += 6
            continue
            
        # In main()
        if line.startswith("    elif cmd == \"gemini\":"):
            # skip until we hit hook
            while i < len(lines) and not lines[i].startswith("    elif cmd == \"hook\":"):
                i += 1
            continue

        new_lines.append(line)
        i += 1
        
    f.write_text("\n".join(new_lines) + "\n", "utf-8")
    print("Done rewriting __main__.py")
    
