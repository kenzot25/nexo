$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-merge-semantic nexo-out\.nexo_cached.json nexo-out\.nexo_semantic_new.json nexo-out\.nexo_semantic.json"
