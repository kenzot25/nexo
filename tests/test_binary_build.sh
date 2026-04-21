#!/bin/bash
set -e

# Integration test for standalone binary builds.
# Verifies that build-binaries.sh produces a functional executable.

echo "--- nexo Binary Build Test ---"

# 1. Run the build script
echo "[1/3] Building local binary..."
chmod +x scripts/build-binaries.sh

PYINSTALLER="$(pwd)/.venv/bin/pyinstaller"
if [ ! -f "$PYINSTALLER" ]; then
    echo "[!] PyInstaller not in .venv - installing now..."
    ./.venv/bin/python -m pip install -q pyinstaller
fi

# Override pyinstaller command for the build script
PATH="$(pwd)/.venv/bin:$PATH" ./scripts/build-binaries.sh

# 2. Verify binary existence
BINARY="dist/nexo"
if [ ! -f "$BINARY" ]; then
    echo "FAIL: dist/nexo not found after build"
    exit 1
fi
echo "Success: Binary generated at $BINARY"

# 3. Verify execution independance
echo "[2/3] Verifying binary execution..."
# Try running it to get version or help
./$BINARY --help > /dev/null
echo "Success: Binary is executable and responsive."

echo "[3/3] Testing 'nexo' command name..."
mv $BINARY dist/nexo-test
./dist/nexo-test --help > /dev/null
echo "Success: Binary works correctly even when renamed."

echo "Binary Build test PASSED."
