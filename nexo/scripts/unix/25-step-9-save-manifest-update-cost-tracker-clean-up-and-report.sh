$(cat nexo-out/.nexo_bin) internal-manifest nexo-out
rm -f nexo-out/.nexo_detect.json nexo-out/.nexo_extract.json nexo-out/.nexo_ast.json nexo-out/.nexo_semantic.json nexo-out/.nexo_analysis.json nexo-out/.nexo_labels.json
rm -f nexo-out/.needs_update 2>/dev/null || true
