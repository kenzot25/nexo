mkdir -p nexo-out
$(cat nexo-out/.nexo_bin) internal-analyze nexo-out/.nexo_extract.json nexo-out/.nexo_detect.json nexo-out "INPUT_PATH"
