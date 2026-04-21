RESULT=$($(cat nexo-out/.nexo_bin) internal-detect-incremental . nexo-out)
echo "$RESULT" > nexo-out/.nexo_incremental.json
NEW_TOTAL=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('new_total', 0))" 2>/dev/null || echo "0")
if [ "$NEW_TOTAL" -eq 0 ]; then
    echo "No files changed since last run. Nothing to update."
    exit 0
fi
echo "$NEW_TOTAL new/changed file(s) to re-extract."
