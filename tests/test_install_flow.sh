#!/bin/bash
set -e

# Sandboxed integration test for nexo installation.
# This mocks a "fresh environment" to verify bootstrapping and CLI command behavior.

TEST_DIR="tests/sandbox-home"
TMP_PROJECT="tests/sandbox-project"
OUT_DIR="tests/install-test-out"

echo "--- nexo Installation Flow Test ---"
echo "Sandbox: $TEST_DIR"

# Cleanup
rm -rf "$TEST_DIR" "$TMP_PROJECT" "$OUT_DIR"
mkdir -p "$TEST_DIR/.local/bin"
mkdir -p "$TMP_PROJECT"

# 1. Setup Mock environment
export HOME="$(pwd)/$TEST_DIR"
export PATH="$HOME/.local/bin:$PATH"

# 2. Run the installer (using local wheel if possible, or source install)
echo "[1/4] Finding compatible Python (>=3.10)..."
PYTHON_CMD="python3"
for cmd in "/opt/homebrew/bin/python3.13" "/opt/homebrew/bin/python3.12" "/opt/homebrew/bin/python3.10" "python3.10" "python3.11" "python3.12"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >/dev/null 2>&1; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done
echo "Using: $PYTHON_CMD"

VENV_DIR="$HOME/.local/share/nexo/venv"
mkdir -p "$VENV_DIR"
"$PYTHON_CMD" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade -q pip
"$VENV_DIR/bin/pip" install -q .

INSTALL_DIR="$HOME/.local/bin"
cat > "$INSTALL_DIR/nexo" <<EOF
#!/usr/bin/env sh
exec "$VENV_DIR/bin/python" -m nexo "\$@"
EOF
chmod +x "$INSTALL_DIR/nexo"

# 3. Verify CLI command is functional
echo "[2/4] Verifying 'nexo' command..."
INSTALLED_BIN=$(command -v nexo)
if [ "$INSTALLED_BIN" != "$INSTALL_DIR/nexo" ]; then
    echo "FAIL: nexo not correctly appearing on PATH"
    echo "Expected: $INSTALL_DIR/nexo"
    echo "Found:    $INSTALLED_BIN"
    exit 1
fi

nexo --help > /dev/null
echo "Success: CLI command is reachable and responsive."

# 4. Test logic inside the tool (Interactive Run / Doctor)
echo "[3/4] Testing 'nexo doctor'..."
cd "$TMP_PROJECT"
# Run doctor - should fail initially because skill not installed
if nexo doctor > /dev/null 2>&1; then
    echo "FAIL: doctor should have failed on fresh project"
    exit 1
fi

echo "[4/4] Testing 'nexo install --local' (Skill setup)..."
nexo install --local
if [ ! -f ".claude/skills/nexo/SKILL.md" ]; then
    echo "FAIL: .claude/skills/nexo/SKILL.md not created"
    exit 1
fi

# Verify doctor passes now
nexo doctor > /dev/null
echo "Success: Skill installation and doctor validation passed."

echo "Integration test PASSED."
