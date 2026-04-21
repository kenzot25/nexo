$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
"LABELS_DICT" -replace "'", '"' | Out-File -FilePath "nexo-out\.nexo_labels_tmp.json" -Encoding utf8
Invoke-Expression "& $BIN internal-label nexo-out 'INPUT_PATH' nexo-out\.nexo_labels_tmp.json"
Remove-Item "nexo-out\.nexo_labels_tmp.json" -ErrorAction SilentlyContinue
