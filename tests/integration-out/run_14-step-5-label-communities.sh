echo '{0: 'General'}' | sed 's/\\/\\\\/g' | sed "s/'/\"/g" > tests/integration-out/nexo-out/.nexo_labels_tmp.json
$(cat tests/integration-out/nexo-out/.nexo_bin) internal-label tests/integration-out/nexo-out "tests/fixtures" tests/integration-out/nexo-out/.nexo_labels_tmp.json
rm tests/integration-out/nexo-out/.nexo_labels_tmp.json
