$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-cache-save nexo-out\.nexo_semantic_new.json"
