#!/bin/bash
set -e

# Build standalone binaries for nexo using PyInstaller.
# Usage: ./scripts/build-binaries.sh

OUTPUT_NAME="nexo"
MAIN_SCRIPT="nexo/__main__.py"

echo "--- nexo Binary Build ---"
echo "Target: $OUTPUT_NAME"

# Check for PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: pyinstaller not found. Run: pip install pyinstaller"
    exit 1
fi

# Determine OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Collect resources
# Note: we use --add-data "source:destination"
# On Unix separator is ':', on Windows it is ';'
SEP=":"
if [[ "$OS" == *"mingw"* || "$OS" == *"msys"* || "$OS" == *"cygwin"* ]]; then
    SEP=";"
fi

echo "Building for $OS ($ARCH)..."

pyinstaller --onefile \
    --name "$OUTPUT_NAME" \
    --add-data "nexo/skill.md$SEP." \
    --add-data "nexo/skill-windows.md$SEP." \
    --add-data "nexo/scripts$SEP.scripts" \
    --collect-all tree_sitter_python \
    --collect-all tree_sitter_javascript \
    --collect-all tree_sitter_typescript \
    --collect-all tree_sitter_go \
    --collect-all tree_sitter_rust \
    --collect-all tree_sitter_java \
    --collect-all tree_sitter_c \
    --collect-all tree_sitter_cpp \
    --collect-all tree_sitter_ruby \
    --collect-all tree_sitter_c_sharp \
    --collect-all tree_sitter_kotlin \
    --collect-all tree_sitter_scala \
    --collect-all tree_sitter_php \
    --collect-all tree_sitter_swift \
    --collect-all tree_sitter_lua \
    --collect-all tree_sitter_zig \
    --collect-all tree_sitter_powershell \
    --collect-all tree_sitter_elixir \
    --collect-all tree_sitter_objc \
    --collect-all tree_sitter_julia \
    --collect-all tree_sitter_verilog \
    --hidden-import networkx \
    --hidden-import watchdog \
    --hidden-import rich \
    "$MAIN_SCRIPT"

echo "Build complete: dist/$OUTPUT_NAME"
