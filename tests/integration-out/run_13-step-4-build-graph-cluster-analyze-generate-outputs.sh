mkdir -p tests/integration-out/nexo-out
$(cat tests/integration-out/nexo-out/.nexo_bin) internal-analyze tests/integration-out/nexo-out/.nexo_extract.json tests/integration-out/nexo-out/.nexo_detect.json tests/integration-out/nexo-out "tests/fixtures"
