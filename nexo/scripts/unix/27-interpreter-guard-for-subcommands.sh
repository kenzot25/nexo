if [ ! -f nexo-out/.nexo_bin ]; then
    NEXO_CMD=$(command -v nexo 2>/dev/null || echo "")
    if [ -n "$NEXO_CMD" ] && "$NEXO_CMD" stats --out-dir . >/dev/null 2>&1; then
        mkdir -p nexo-out
        echo "$NEXO_CMD" > nexo-out/.nexo_bin
    else
        # Fallback to python
        if command -v python3 >/dev/null 2>&1; then PYTHON="python3"; else PYTHON="python"; fi
        if ! "$PYTHON" -c "import nexo" 2>/dev/null; then
            echo "ERROR: nexo is unavailable." >&2
            exit 1
        fi
        mkdir -p nexo-out
        echo "$PYTHON -m nexo" > nexo-out/.nexo_bin
    fi
fi
