$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-export gephi nexo-out"
