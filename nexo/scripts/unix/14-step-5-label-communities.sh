echo 'LABELS_DICT' | sed 's/\\/\\\\/g' | sed "s/'/\"/g" > nexo-out/.nexo_labels_tmp.json
$(cat nexo-out/.nexo_bin) internal-label nexo-out "INPUT_PATH" nexo-out/.nexo_labels_tmp.json
rm nexo-out/.nexo_labels_tmp.json
