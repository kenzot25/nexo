#!/bin/bash
set -e

# Integration test for nexo template scripts.
# Runs the full pipeline on tests/fixtures/ using ASCII-only mode.

SCRIPT_DIR="nexo/scripts/unix"
TEST_CORPUS="tests/fixtures"
OUT_DIR="tests/integration-out"
PYTHON_INTERPRETER=$(pwd)/.venv/bin/python

if [ ! -f "$PYTHON_INTERPRETER" ]; then
    echo "ERROR: Virtual environment not found at .venv. Run 'make setup' first."
    exit 1
fi

if [ "$USE_BINARY" = "1" ]; then
    NEXO_BIN=$(ls dist/nexo* 2>/dev/null | head -1)
    if [ ! -f "$NEXO_BIN" ]; then
        echo "ERROR: Binary not found in dist/. Run 'make build-binary' first."
        exit 1
    fi
    echo "Using Binary: $NEXO_BIN"
    PYTHON_EXEC="$NEXO_BIN"
else
    PYTHON_EXEC="$PYTHON_INTERPRETER -m nexo"
    echo "Using Python: $PYTHON_EXEC"
fi

# Cleanup previous run
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Step 1: Resolve interpreter (Step 1 template)
echo "[1/7] Step 1: Ensure installed / Resolve interpreter"
mkdir -p "$OUT_DIR/nexo-out"
echo "$PYTHON_EXEC" > "$OUT_DIR/nexo-out/.nexo_bin"

# Helper function to run a script template with replacements
run_template() {
    local template_name=$1
    local script_path="$SCRIPT_DIR/$template_name"
    local temp_script="$OUT_DIR/run_$template_name"
    
    cp "$script_path" "$temp_script"
    
    # Replace common placeholders
    sed -i '' "s|INPUT_PATH|$TEST_CORPUS|g" "$temp_script"
    sed -i '' "s|PATH_TO_DIR|$(pwd)/$TEST_CORPUS|g" "$temp_script"
    sed -i '' "s|LABELS_DICT|{0: 'General'}|g" "$temp_script"
    sed -i '' "s|nexo-out|$OUT_DIR/nexo-out|g" "$temp_script"
    
    # Run it
    bash "$temp_script"
}

# Step 2: Detect files
echo "[2/7] Step 2: Detect files"
run_template "03-step-2-detect-files.sh"
if [ ! -f "$OUT_DIR/nexo-out/.nexo_detect.json" ]; then
    echo "FAIL: .nexo_detect.json missing"
    exit 1
fi

# Step 3: AST Extraction
echo "[3/7] Step 3: AST Extraction"
run_template "06-part-a-structural-extraction-for-code-files.sh"
if [ ! -f "$OUT_DIR/nexo-out/.nexo_ast.json" ]; then
    echo "FAIL: .nexo_ast.json missing"
    exit 1
fi

# Step 4: Merge (Mocked Semantic)
echo "[4/7] Step 4: Merge Extraction"
# Create a dummy semantic file if it doesn't exist
echo '{"nodes":[], "edges":[], "input_tokens": 0, "output_tokens": 0}' > "$OUT_DIR/nexo-out/.nexo_semantic.json"
run_template "12-part-c-merge-ast-semantic-into-final-extraction.sh"

# Step 5: Build Graph & Cluster
echo "[5/7] Step 5: Build, Cluster, Analyze"
run_template "13-step-4-build-graph-cluster-analyze-generate-outputs.sh"

# Step 6: Label Communities
echo "[6/7] Step 7: Label Communities"
run_template "14-step-5-label-communities.sh"

# Step 7: Final Report & Cleanup
echo "[7/7] Step 9: Save manifestation and report"
run_template "25-step-9-save-manifest-update-cost-tracker-clean-up-and-report.sh"

# Final Assertions
echo "--- Verifying Outputs ---"
if [ ! -f "$OUT_DIR/nexo-out/graph.json" ]; then echo "FAIL: graph.json missing"; exit 1; fi
if [ ! -f "$OUT_DIR/nexo-out/GRAPH_REPORT.md" ]; then echo "FAIL: GRAPH_REPORT.md missing"; exit 1; fi

NODE_COUNT=$(grep -o '"id"' "$OUT_DIR/nexo-out/graph.json" | wc -l)
echo "Success: Graph generated with $NODE_COUNT nodes."
echo "Integration test PASSED."
