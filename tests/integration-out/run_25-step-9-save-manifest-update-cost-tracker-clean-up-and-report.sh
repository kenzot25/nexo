$(cat tests/integration-out/nexo-out/.nexo_bin) internal-manifest tests/integration-out/nexo-out
rm -f tests/integration-out/nexo-out/.nexo_detect.json tests/integration-out/nexo-out/.nexo_extract.json tests/integration-out/nexo-out/.nexo_ast.json tests/integration-out/nexo-out/.nexo_semantic.json tests/integration-out/nexo-out/.nexo_analysis.json tests/integration-out/nexo-out/.nexo_labels.json
rm -f tests/integration-out/nexo-out/.needs_update 2>/dev/null || true
