$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-merge nexo-out\.nexo_ast.json nexo-out\.nexo_semantic.json nexo-out\.nexo_extract.json"
