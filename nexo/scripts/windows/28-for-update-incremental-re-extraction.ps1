$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-merge-incremental . nexo-out\.nexo_incremental.json"
