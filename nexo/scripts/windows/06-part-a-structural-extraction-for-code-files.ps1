$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-extract nexo-out\.nexo_detect.json nexo-out\.nexo_ast.json"
