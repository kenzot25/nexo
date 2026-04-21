# Resolve the 'nexo' command (binary or python)
mkdir -p nexo-out
NEXO_CMD=$(command -v nexo 2>/dev/null || echo "")

if [ -n "$NEXO_CMD" ]; then
    # Verify it works (could be a broken script or a standalone binary)
    if "$NEXO_CMD" stats --out-dir . >/dev/null 2>&1; then
        echo "$NEXO_CMD" > nexo-out/.nexo_bin
        exit 0
    fi
fi

# Fallback to Python if binary is missing or broken
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "ERROR: Neither 'nexo' binary nor 'python' found." >&2
    exit 1
fi

if ! "$PYTHON" -c "import nexo" 2>/dev/null; then
    "$PYTHON" -m pip install nexo -q 2>/dev/null || "$PYTHON" -m pip install nexo -q --break-system-packages 2>&1 | tail -3
fi

if ! "$PYTHON" -c "import nexo" 2>/dev/null; then
    echo "ERROR: nexo is unavailable." >&2
    exit 1
fi

# Save the python execution command
echo "$PYTHON -m nexo" > nexo-out/.nexo_bin
