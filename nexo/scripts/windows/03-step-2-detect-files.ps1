$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-detect 'INPUT_PATH'" > nexo-out\.nexo_detect.json
