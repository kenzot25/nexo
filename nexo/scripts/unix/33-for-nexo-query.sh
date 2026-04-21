if [ ! -f nexo-out/.nexo_bin ]; then
    NEXO_CMD=$(command -v nexo 2>/dev/null || echo "")
    if [ -n "$NEXO_CMD" ] && "$NEXO_CMD" stats --out-dir . >/dev/null 2>&1; then
        mkdir -p nexo-out
        echo "$NEXO_CMD" > nexo-out/.nexo_bin
    else
        if command -v python3 >/dev/null 2>&1; then PYTHON="python3"; else PYTHON="python"; fi
        mkdir -p nexo-out
        echo "$PYTHON -m nexo" > nexo-out/.nexo_bin
    fi
fi

if [ ! -f nexo-out/graph.json ]; then
    echo "ERROR: No graph found. Run /nexo <path> first to build the graph."
    exit 1
fi
